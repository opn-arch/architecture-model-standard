"""Tests for viewer comment textarea, localStorage persistence, and YAML export/import."""

import tempfile
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

import pytest

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


class _ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._script = {"type": dict(attrs).get("type"), "text": ""}

    def handle_data(self, data):
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append(self._script)
            self._script = None


def _viewer_parts(html):
    parser = _ScriptParser()
    parser.feed(html)
    data = json.loads(next(s["text"] for s in parser.scripts if s["type"] == "application/json"))
    script = next(s["text"] for s in parser.scripts if s["type"] != "application/json")
    return data, script


@pytest.fixture
def minimal_model():
    return _parse_raw(
        {
            "meta": {"project": "test-proj", "schema_version": "1.3"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Foo", "status": "ACTIVE"},
                ],
            },
            "relationships": [],
        }
    )


@pytest.fixture
def html_output(minimal_model, tmp_path):
    out = tmp_path / "viewer.html"
    generate_html_viewer(minimal_model, out)
    return out.read_text()


def test_comment_textarea_class(html_output):
    assert "comment-textarea" in html_output


def test_comment_section_css(html_output):
    assert ".comment-section" in html_output


def test_localstorage_reference(html_output):
    assert "localStorage" in html_output


def test_export_comments_function(html_output):
    assert "exportComments" in html_output


def test_import_comments_function(html_output):
    assert "importComments" in html_output


def test_toolbar_buttons_present(html_output):
    assert "Export Comments" in html_output
    assert "Import Comments" in html_output


def test_save_comment_function(html_output):
    assert "saveComment" in html_output


def test_comment_placeholder(html_output):
    assert "Add notes about this entity" in html_output


def test_same_basename_modules_have_distinct_persistent_comments(minimal_model, tmp_path, monkeypatch):
    modules = {
        "src/shared.py": {"name": "shared", "doc": "", "funcs": [], "classes": [], "consts": []},
        "subsystems/api/src/shared.py": {"name": "shared", "doc": "", "funcs": [], "classes": [], "consts": []},
    }
    monkeypatch.setattr("architecture_model.core.visualize._build_module_data", lambda _repo: modules)
    html = generate_html_viewer(minimal_model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    data, script = _viewer_parts(html)
    harness = f"""
const vm=require('vm'); const store={{}}; const rendered=[];
const element={{addEventListener:()=>{{}},click:()=>{{}},value:'',files:[]}};
let textarea=null; const content={{dataset:{{}},addEventListener:()=>{{}},querySelectorAll:()=>[]}};
Object.defineProperty(content,'innerHTML',{{set(value){{this.html=value; const m=value.match(/data-comment-id="([^"]+)"/); textarea=m?{{value:'',dataset:{{commentKind:'module',commentId:m[1]}},addEventListener:(n,fn)=>textarea[n]=fn}}:null; if(textarea)rendered.push(textarea);}},get(){{return this.html||'';}}}});
content.querySelector=s=>s==='.comment-textarea'?textarea:null;
const dataElement={{...element,textContent:{json.dumps(json.dumps(data))}}};
const context={{console,Blob,URL,alert:()=>{{}},MutationObserver:function(){{this.observe=()=>{{}}}},
 document:{{getElementById:id=>id==='viewer-data'?dataElement:id==='content'?content:element,querySelectorAll:()=>[],querySelector:()=>({{classList:{{remove:()=>{{}},toggle:()=>{{}}}},addEventListener:()=>{{}}}}),createElement:()=>element}},
 localStorage:{{get length(){{return Object.keys(store).length}},key:i=>Object.keys(store)[i],getItem:k=>store[k]||null,setItem:(k,v)=>store[k]=v}},innerWidth:1200,atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context; vm.createContext(context); vm.runInContext({json.dumps(script)},context);
context.showModule('src/shared.py'); if(!textarea) throw new Error('module textarea missing'); textarea.value='top <b>safe</b> snow'; textarea.input();
context.showModule('subsystems/api/src/shared.py'); textarea.value='subsystem "safe"'; textarea.input();
context.showModule('src/shared.py');
if(rendered.length!==3 || textarea.value!=='top <b>safe</b> snow') throw new Error(JSON.stringify({{rendered:rendered.length,value:textarea&&textarea.value}}));
const keys=Object.keys(store); if(keys.length!==2 || keys[0]===keys[1] || !keys.every(k=>k.includes(':module:'))) throw new Error(JSON.stringify(keys));
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_module_comment_export_import_roundtrip_validates_registry(minimal_model, tmp_path, monkeypatch):
    modules = {
        "src/shared.py": {"name": "shared", "doc": "", "funcs": [], "classes": [], "consts": []},
    }
    monkeypatch.setattr("architecture_model.core.visualize._build_module_data", lambda _repo: modules)
    html = generate_html_viewer(minimal_model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    data, script = _viewer_parts(html)
    hostile = "hostile </textarea> \u96ea \" '"
    imported = f'"module:src%2Fshared.py":\n  comment: |\n    {hostile}\n"module:missing.py":\n  comment: |\n    rejected\nCOMP-1:\n  comment: |\n    legacy entity'
    harness = f"""
const vm=require('vm'); const writes=[]; let exported='';
const element={{addEventListener:()=>{{}},click:()=>{{}},value:'',files:[{{}}]}}; const content={{...element,dataset:{{}},querySelectorAll:()=>[],querySelector:()=>null}};
const storage={json.dumps({'arch-comment:test-proj:COMP-1': 'legacy entity', 'arch-comment:test-proj:module:src%2Fshared.py': hostile})};
const context={{console,Blob:function(parts){{exported=parts.join('')}},URL:{{createObjectURL:()=>''}},alert:()=>{{}},MutationObserver:function(){{this.observe=()=>{{}}}},
 FileReader:function(){{this.readAsText=()=>this.onload({{target:{{result:{json.dumps(imported)}}}}})}},
 document:{{getElementById:id=>id==='viewer-data'?{{...element,textContent:{json.dumps(json.dumps(data))}}}:id==='content'?content:element,querySelectorAll:()=>[],querySelector:()=>({{...element,classList:{{remove:()=>{{}},toggle:()=>{{}}}}}}),createElement:()=>element}},
 localStorage:{{get length(){{return Object.keys(storage).length}},key:i=>Object.keys(storage)[i],getItem:k=>storage[k]||null,setItem:(k,v)=>writes.push([k,v])}},innerWidth:1200,atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context;vm.createContext(context);vm.runInContext({json.dumps(script)},context);context.exportComments();context.importComments(element);
if(!exported.includes('"module:src%2Fshared.py":') || !exported.includes('COMP-1:')) throw new Error(exported);
if(writes.length!==2 || !writes.some(x=>x[0].endsWith(':module:src%2Fshared.py')&&x[1].includes('</textarea>')) || !writes.some(x=>x[0].endsWith(':COMP-1'))) throw new Error(JSON.stringify(writes));
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_module_comment_storage_failure_and_inline_syntax_are_safe(minimal_model, tmp_path, monkeypatch):
    modules = {
        "src/hostile.py": {"name": "hostile", "doc": "</script><script>globalThis.pwned=1</script>", "funcs": [], "classes": [], "consts": []},
    }
    monkeypatch.setattr("architecture_model.core.visualize._build_module_data", lambda _repo: modules)
    html = generate_html_viewer(minimal_model, tmp_path / "viewer.html", repo_path=tmp_path).read_text()
    data, script = _viewer_parts(html)
    js_path = tmp_path / "viewer.js"
    js_path.write_text(script)
    syntax = subprocess.run(["node", "--check", js_path], capture_output=True, text=True)
    assert syntax.returncode == 0, syntax.stderr
    harness = f"""
const vm=require('vm'); const element={{addEventListener:()=>{{}},click:()=>{{}},value:'',files:[]}};
const textarea={{value:'',dataset:{{commentKind:'module',commentId:'src/hostile.py'}},addEventListener:()=>{{}}}};
const content={{...element,dataset:{{}},innerHTML:'',querySelectorAll:()=>[],querySelector:s=>s==='.comment-textarea'?textarea:null}};
const context={{console,Blob,URL,alert:()=>{{}},MutationObserver:function(){{this.observe=()=>{{}}}},document:{{getElementById:id=>id==='viewer-data'?{{...element,textContent:{json.dumps(json.dumps(data))}}}:id==='content'?content:element,querySelectorAll:()=>[],querySelector:()=>({{...element,classList:{{remove:()=>{{}},toggle:()=>{{}}}}}}),createElement:()=>element}},localStorage:new Proxy({{}},{{get(){{throw new Error('denied')}}}}),innerWidth:1200,atob,btoa,escape,unescape,encodeURIComponent,decodeURIComponent}};
context.window=context;vm.createContext(context);vm.runInContext({json.dumps(script)},context);context.showModule('src/hostile.py');if(context.pwned||content.innerHTML.includes('<script>'))throw new Error(content.innerHTML);
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
