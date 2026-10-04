Storage structure:

Distinct json files per profile.
Seperate directory of each profile.
Example:
|> Storage
    |> Profiles
        |> 1
            |> Workbooks
                |> 1
                    |> Sources
                    |> Outputs
                    | chat.json
                    | config.json
                    | sources.json
                    | outputs.json
                |> 2
                |> {id}
            |> Callers
                | caller_1.py
                | caller_{id}.py
            |> Tools
                |> 1
                    | main.py
                    | **.py
                    | schema.json
                    | meta.json
                    | README.md
                |> {id}
            | api_keys.json
            | callers.json
            | tools.json
            | workbooks.json
    | profiles.json

each row of:
- api_keys.json:
    {
        id: int, name: str, description: str, 
        meta: object,
        created_at, updated_at
    }
- callers.json:
    {
        id: int, name: str, description: str,
        created_at, updated_at
    }
- tools.json:
    {
        id: int, title: str, description: str,
        created_at, updated_at
    }
- workbooks.json
    {
        id: int, title: str, description: str,
        created_at, updated_at
    }
schema.json is the schema of all the available tools in the package
- chat.json
    {
        role: str, content: str, meta: object,
        created_at, updated_at
    }
- sources.json
    {
        id: int, name: int, description: int, kind: link|local
        created_at, updated_at
    }
- outputs.json
    {
        id: int, name: int, description: int,
        created_at, updated_at
    }

caller file structure:

```python

# Mandatory caller interface:
def INVOKE(**settings):
    return {
        "success": True,
        "model": settings["model"],
        "message": {"role": "assistant", "content": "..."},
    }

def MODEL(**settings):
    return {"success": True, "models": [{"id": "...", "name": "..."}]}

```




This is how the app storage is stored inside local computer.
Now, we need a python Storage API. such that:

```python
STORAGE = Storage("base_dir")

profiles_manager = STORAGE.profiles -> ProfilesManager

profile = profiles_manager.load("Profile1") # returns a Profile object
profile.update, delete

wb_manager = profile.workbooks # WBManager Object
wb_manager.[list()->list[Workbook]|load(id)->Workbook|create(title, description)->Workbook|delete(id)]

wb = wb_manager.load(1)

wb_chat = wb.chat # Returns WBChat object
wb_chat.add(msg_type, content, meta) -> None

wb.config.[set(key, value)|get(key)|all()->dict]

wb_sources = wb.sources # WBSources object
wb.sources.add_file(name, description, src=path, copy=True/False) # add source from local file
wb.sources.add_url(name, description, src=link, download=True/False) # add from url
wb.sources.add_content(name, description, content=path, encoding='utf-8')
wb_sources.[delete(id)|update(id, updates...)->Source]

src = wb_sources.load(id)
src.read() -> content
src.write(content)
src.delete()
src.rename(new_name)
src.redescribe(new_description)

wb_outputs = wb.outputs # WBOutputs object
wb_outputs.add("name", "description", content) -> WBOutput
wb_outputs.[delete(id)|update(id, * name, desc, content)->WBOutput]

otpt = wb_outputs.load(id)
otpt.read() -> content
otpt.write(content)
otpt.delete()
otpt.rename(new_name)
otpt.redescribe(new_description)

wb_callers = wb.callers -> WBCallers
wbcl = wb_callers.load(id)->WBCaller
resp = wbcl.invoke(**kwargs)
wbcl.delete(...)
wbcl.update(name, desc)

wb_callers.add(name, desc, content)
wb_callers.delete(id)
wb_callers.update(id, ...)

wb_apiks = wb.api_keys -> WBApiKeys
wb_apiks.add, delete, update, get
wbap = wb_apiks.get(1) -> WBApiKey
wbap.delete, update
caller.invoke(**kwargs) # caller selection is independent of API-key credentials

wb_tools = wb.tools -> WBToolPackager
wb_tools.add, update, delete
wb_tools.get_schema(id=None) # if none, returns full schema file.

wbtl = wb_tools.load(id) -> WBTool
wbtl.make_call(fn_name, arguments: dict) -> some_response
```

we can have a function called initialize_storage. that creates storage in DOCUMENTS folder. with the folder name called: PAWM_DATA


