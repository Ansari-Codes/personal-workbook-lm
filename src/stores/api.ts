const API_BASE = 'http://127.0.0.1:8080/api'
const API_REQUEST_TIMEOUT_MS = 15_000;

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD';
type QueryParams = Record<string, string | number | boolean | string[] | number[] | boolean[] | null | undefined>;

export class ApiError extends Error {
    constructor(
        message: string,
        readonly status: number | null,
        readonly endpoint: string,
        readonly detail?: unknown,
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

function responseDetail(payload: unknown): string | undefined {
    if (typeof payload === 'string') return payload.trim() || undefined;
    if (typeof payload !== 'object' || payload === null || !('detail' in payload)) {
        return undefined;
    }

    const detail = payload.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail.map((issue: unknown) => {
            if (typeof issue !== 'object' || issue === null) return String(issue);
            const item = issue as { loc?: unknown[]; msg?: unknown };
            const location = item.loc?.slice(1).join('.');
            const message = typeof item.msg === 'string' ? item.msg : 'Invalid value';
            return location ? `${location}: ${message}` : message;
        }).join('; ');
    }
    if (detail !== undefined && detail !== null) return JSON.stringify(detail);
    return undefined;
}

/**
 * Makes an HTTP request to the API_BASE.
 * @template TResponse The expected shape of the returned JSON data.
 * @template TBody The shape of the payload being sent (defaults to any).
 */
export async function apiRequest<TResponse = any, TBody = any>(
    endpoint: string,
    method: HttpMethod = 'GET',
    data: TBody | null = null,
    params: QueryParams = {},
    signal?: AbortSignal,
    timeoutMs: number | null = API_REQUEST_TIMEOUT_MS,
): Promise<TResponse | null> {

    const formattedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = new URL(`${API_BASE}${formattedEndpoint}`);

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
                value.forEach(val => url.searchParams.append(key, String(val)));
            } else {
                url.searchParams.append(key, String(value));
            }
        }
    });

    const timeoutSignal = timeoutMs === null ? undefined : AbortSignal.timeout(timeoutMs);
    const requestSignal = signal && timeoutSignal
        ? AbortSignal.any([signal, timeoutSignal])
        : signal ?? timeoutSignal;
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const options: RequestInit = {
        method: method.toUpperCase(),
        headers: isFormData ? undefined : { 'Content-Type': 'application/json' },
        signal: requestSignal,
    };

    if (data !== null && data !== undefined && options.method !== 'GET' && options.method !== 'HEAD') {
        options.body = isFormData ? data : JSON.stringify(data);
    }

    let response: Response;
    try {
        response = await fetch(url.toString(), options);
    } catch (cause) {
        if (timeoutSignal?.aborted) {
            throw new ApiError(`The API request timed out after ${timeoutMs! / 1000} seconds.`, null, url.toString(), cause);
        }
        const reason = cause instanceof Error ? cause.message : String(cause);
        const error = new ApiError(`Could not reach the API: ${reason}`, null, url.toString(), cause);
        console.error(`[api] ${options.method} ${url} failed`, error);
        throw error;
    }

    if (!response.ok) {
        let rawBody: string;
        try {
            rawBody = await response.text();
        } catch (cause) {
            if (timeoutSignal?.aborted) {
                throw new ApiError(`The API request timed out after ${timeoutMs! / 1000} seconds.`, null, url.toString(), cause);
            }
            throw cause;
        }
        let payload: unknown = rawBody;
        try {
            payload = rawBody ? JSON.parse(rawBody) : undefined;
        } catch {
            payload = rawBody;
        }
        const detail = responseDetail(payload);
        const message = detail ?? response.statusText ?? 'Request failed';
        const error = new ApiError(message, response.status, url.toString(), payload);
        console.error(`[api] ${options.method} ${url} returned ${response.status}`, error);
        throw error;
    }

    if (response.status === 204 || response.headers.get('content-length') === '0') {
        return null;
    }

    try {
        return (await response.json()) as TResponse;
    } catch (cause) {
        if (timeoutSignal?.aborted) {
            throw new ApiError(`The API request timed out after ${timeoutMs! / 1000} seconds.`, null, url.toString(), cause);
        }
        const reason = cause instanceof Error ? cause.message : String(cause);
        const error = new ApiError(`The API returned invalid JSON: ${reason}`, response.status, url.toString(), cause);
        console.error(`[api] ${options.method} ${url} returned invalid JSON`, error);
        throw error;
    }
}

export async function apiStreamRequest<TEvent, TBody>(
    endpoint: string,
    data: TBody,
    onEvent: (event: TEvent) => void,
    signal?: AbortSignal,
): Promise<void> {
    const formattedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_BASE}${formattedEndpoint}`;
    let response: Response;
    try {
        response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
            body: JSON.stringify(data),
            signal,
        });
    } catch (cause) {
        const reason = cause instanceof Error ? cause.message : String(cause);
        throw new ApiError(`Could not reach the API: ${reason}`, null, url, cause);
    }

    if (!response.ok) {
        const rawBody = await response.text();
        let payload: unknown = rawBody;
        try {
            payload = rawBody ? JSON.parse(rawBody) : undefined;
        } catch {
            payload = rawBody;
        }
        throw new ApiError(responseDetail(payload) ?? response.statusText ?? 'Request failed', response.status, url, payload);
    }

    if (!response.body) throw new ApiError('The API response is not readable.', response.status, url);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    function dispatchLine(line: string): void {
        if (!line.startsWith('data:')) return;
        const dataLine = line.slice(5).trim();
        if (!dataLine || dataLine === '[DONE]') return;
        onEvent(JSON.parse(dataLine) as TEvent);
    }

    try {
        while (true) {
            const { done, value } = await reader.read();
            buffer += decoder.decode(value, { stream: !done });
            const lines = buffer.split('\n');
            buffer = done ? '' : lines.pop() ?? '';
            for (const line of lines) dispatchLine(line.replace(/\r$/, ''));
            if (done) {
                if (buffer) dispatchLine(buffer.replace(/\r$/, ''));
                break;
            }
        }
    } finally {
        reader.releaseLock();
    }
}
