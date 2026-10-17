package main

import (
 "encoding/json"
 "io"
 "net/http"
 "strings"
 "testing"
)
type roundTrip func(*http.Request)(*http.Response,error)
func (f roundTrip)RoundTrip(r *http.Request)(*http.Response,error){return f(r)}
func mockHTTP(t *testing.T,body string,inspect func(*http.Request)){
 t.Helper();old:=http.DefaultTransport
 http.DefaultTransport=roundTrip(func(r *http.Request)(*http.Response,error){if inspect!=nil{inspect(r)};return &http.Response{StatusCode:200,Body:io.NopCloser(strings.NewReader(body)),Header:make(http.Header),Request:r},nil})
 t.Cleanup(func(){http.DefaultTransport=old})
}
func TestURL(t *testing.T){
 if err:=validateURL(defaultURL);err!=nil{t.Fatal(err)}
 for _,u:=range []string{"http://script.google.com/a/exec","https://evil.test/exec",defaultURL+"?key=x","https://script.google.com:443/a/exec"}{if validateURL(u)==nil{t.Fatalf("accepted %s",u)}}
}
func TestPostSecret(t *testing.T){
 mockHTTP(t,`{"ok":true,"data":[],"meta":{"total":0}}`,func(r *http.Request){
  if r.Method!="POST" || strings.Contains(r.URL.String(),"test-secret"){t.Fatal("invalid transport")}
  var b map[string]interface{};json.NewDecoder(r.Body).Decode(&b)
  if b["api_key"]!="test-secret" || b["action"]!="list"{t.Fatal("invalid body")}
 })
 _,err:=requestAPI(defaultURL,"test-secret","list",nil);if err!=nil{t.Fatal(err)}
}
func TestAPIError(t *testing.T){
 mockHTTP(t,`{"ok":false,"status":401,"error":{"message":"Clave inválida"}}`,nil)
 _,err:=requestAPI(defaultURL,"x","list",nil);if err==nil || err.Error()!="Clave inválida"{t.Fatal(err)}
}
func TestHTML(t *testing.T){mockHTTP(t,"<html>login</html>",nil);if _,err:=requestAPI(defaultURL,"x","list",nil);err==nil{t.Fatal("accepted HTML")}}
func TestInvalidAction(t *testing.T){a:=&App{endpoint:defaultURL,key:"x"};if _,err:=a.Call("execute",nil);err==nil{t.Fatal("accepted action")}}
func TestConfigurationNeverReturnsKey(t *testing.T){
 a:=&App{endpoint:defaultURL,key:"private-value"};cfg,err:=a.Configuration();if err!=nil{t.Fatal(err)}
 data,_:=json.Marshal(cfg);if strings.Contains(string(data),a.key){t.Fatal("secret leaked to UI")}
}
