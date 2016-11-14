var openerplib={};openerplib.json_rpc=function(c,b,g,a){var f={jsonrpc:"2.0",params:g,id:Math.floor((Math.random()*1000000000)+1)};if(b){f.method=b}var e=new XMLHttpRequest();e.open("POST",c,true);e.setRequestHeader("Content-Type","application/json");e.onreadystatechange=function(){if(e.readyState!==4||!a){return}var i=e.getResponseHeader("Content-Type");if(e.status!==200){a("Offline",null)}else{if(i.indexOf("application/json")!==0){a('Expected JSON encoded response, found "'+i+'"',null)}else{var h=JSON.parse(this.responseText);a(h.error||null,h.result||null)}}};e.ontimeout=function(){a("Timeout",null)};try{e.send(JSON.stringify(f))}catch(d){a(d,null)}};openerplib.Service=function(b,a){var c=this;this.con=b;this.service=a;this.exec=function(f,d,e){c.con.send(c.service,f,d,e)}};openerplib.Model=function(a,c){var b=this;this.service=new openerplib.Service(a,"object");this.con=a;this.model=c;this.exec=function(g,d,e,f){b.service.exec("execute_kw",[a.database,a.user_id,a._password,b.model,g,d,e],f)}};openerplib.JsonRPCConnector=function(e,f,c,d,a){var b=this;this._url=e;this._url_jsonrpc=e+"/jsonrpc";this._password=d;this.login=c;this.database=f;this.user_id=a;this.session_id=null;this.user_context=null;this.authenticate=function(i){var h={db:b.database,login:b.login,password:b._password};var g=b._url+"/web/session/authenticate";openerplib.json_rpc(g,null,h,function(k,j){if(k===null){b.session_id=j.session_id;b.user_id=j.uid;b.user_context=j.user_context}if(i){i(k,j)}})};this.send=function(h,j,g,i){openerplib.json_rpc(b._url_jsonrpc,"call",{service:h,method:j,args:g},i)};this.get_service=function(g){return new openerplib.Service(b,g)};this.get_model=function(g){return new openerplib.Model(b,g)}};openerplib.get_connection=function(f,a,c,g,b,e){if(!c){c=8069}var d=f+":"+c.toString();switch(a){case"jsonrpcs":d="https://"+d;break;default:d="http://"+d;break}return new openerplib.JsonRPCConnector(d,g,b,e,null)};