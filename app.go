package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "net/url"
 "os"
 "path/filepath"
 "strings"
 "sync"
 "time"
)

const defaultURL = "https://script.google.com/macros/s/AKfycby7ga3OfgyTcNRbPgm4YvkAC8va2sCf37JRywtjytovzFHUfGgAse-s_WjXu1Nl89An/exec"

type App struct { mu sync.Mutex; endpoint string; key string }
type Config struct { URL string `json:"url"`; Configured bool `json:"configured"` }
type storedConfig struct { URL string `json:"url"`; Secret []byte `json:"secret"` }
type Response struct {
 OK bool `json:"ok"`
 Status int `json:"status"`
 Data json.RawMessage `json:"data"`
 Meta struct { Total int `json:"total"`; Limit int `json:"limit"`; Offset int `json:"offset"` } `json:"meta"`
 Error struct { Code string `json:"code"`; Message string `json:"message"` } `json:"error"`
}

func configPath() (string,error) {
 dir,err:=os.UserConfigDir(); if err!=nil{return "",err}
 // Use a separate file; legacy Python configuration remains untouched.
 return filepath.Join(dir,"PrimerCRM","connection-go.json"),nil
}
func validateURL(endpoint string) error {
 u,err:=url.Parse(endpoint)
 if err!=nil || u.Scheme!="https" || u.Host!="script.google.com" || u.User!=nil || u.RawQuery!="" || u.Fragment!="" || !strings.HasSuffix(u.Path,"/exec") {
  return errors.New("Usa la URL HTTPS de Apps Script terminada en /exec, sin parámetros")
 }
 return nil
}
func (a *App) Configuration() (Config,error) {
 a.mu.Lock();defer a.mu.Unlock()
 if a.key!="" {return Config{a.endpoint,true},nil}
 path,err:=configPath();if err!=nil{return Config{},err}
 raw,err:=os.ReadFile(path)
 if os.IsNotExist(err){return Config{defaultURL,false},nil};if err!=nil{return Config{},errors.New("No se pudo leer la configuración local")}
 var cfg storedConfig
 if json.Unmarshal(raw,&cfg)!=nil || validateURL(cfg.URL)!=nil{return Config{defaultURL,false},errors.New("Configuración dañada; vuelve a ingresar URL y clave")}
 key,err:=unprotect(cfg.Secret);if err!=nil{return Config{cfg.URL,false},errors.New("No se pudo descifrar la clave para este usuario de Windows")}
 a.endpoint=cfg.URL;a.key=string(key)
 return Config{cfg.URL,true},nil
}
func (a *App) SaveConfiguration(endpoint,key string) error {
 a.mu.Lock();defer a.mu.Unlock()
 endpoint=strings.TrimSpace(endpoint);if err:=validateURL(endpoint);err!=nil{return err}
 if key=="" {key=a.key};if key=="" {return errors.New("Ingresa tu API key")}
 if _,err:=requestAPI(endpoint,key,"list",map[string]interface{}{"limit":1});err!=nil{return err}
 encrypted,err:=protect([]byte(key));if err!=nil{return errors.New("Windows no pudo cifrar la clave")}
 path,err:=configPath();if err!=nil{return err}
 if err=os.MkdirAll(filepath.Dir(path),0700);err!=nil{return errors.New("No se pudo crear la carpeta de configuración")}
 raw,err:=json.Marshal(storedConfig{endpoint,encrypted});if err!=nil{return err}
 // One atomic replacement keeps URL and encrypted credential consistent.
 temp,err:=os.CreateTemp(filepath.Dir(path),"connection-*.tmp");if err!=nil{return err}
 name:=temp.Name();defer os.Remove(name)
 if _,err=temp.Write(raw);err!=nil{temp.Close();return err}
 if err=temp.Close();err!=nil{return err}
 if err=replaceConfig(name,path);err!=nil{return errors.New("No se pudo guardar la configuración cifrada")}
 a.endpoint=endpoint;a.key=key
 return nil
}
func (a *App) Call(action string,params map[string]interface{}) (Response,error) {
 a.mu.Lock();defer a.mu.Unlock()
 if a.key=="" {return Response{},errors.New("Configura la conexión primero")}
 switch action {case "list","get","create","update","delete":default:return Response{},errors.New("Acción inválida")}
 return requestAPI(a.endpoint,a.key,action,params)
}
func requestAPI(endpoint,key,action string,params map[string]interface{}) (Response,error) {
 var result Response
 if err:=validateURL(endpoint);err!=nil{return result,err}
 body:=map[string]interface{}{}
 for k,v:=range params{body[k]=v};body["api_key"]=key;body["action"]=action
 raw,err:=json.Marshal(body);if err!=nil{return result,err}
 req,err:=http.NewRequest("POST",endpoint,bytes.NewReader(raw));if err!=nil{return result,err}
 req.Header.Set("Content-Type","application/json")
 client:=&http.Client{Timeout:45*time.Second,CheckRedirect:func(req *http.Request,via []*http.Request)error{
  if len(via)>8{return errors.New("Demasiadas redirecciones")}
  if req.URL.Scheme!="https" || (req.URL.Host!="script.google.com" && req.URL.Host!="script.googleusercontent.com") {return errors.New("Revisa que Google permita acceso sin iniciar sesión")}
  return nil
 }}
 resp,err:=client.Do(req)
 if err!=nil{return result,errors.New("No se pudo completar la conexión. Revisa internet y permisos de Google. Si estabas guardando, actualiza la lista antes de repetir")}
 defer resp.Body.Close()
 if resp.StatusCode!=200{return result,fmt.Errorf("Google devolvió HTTP %d; revisa URL y permisos",resp.StatusCode)}
 data,err:=io.ReadAll(io.LimitReader(resp.Body,8000001));if err!=nil{return result,errors.New("Respuesta incompleta; actualiza antes de repetir una escritura")}
 if len(data)>8000000{return result,errors.New("Respuesta demasiado grande")}
 if json.Unmarshal(data,&result)!=nil{return result,errors.New("Google no devolvió JSON. Verifica la URL /exec y el acceso para cualquier persona")}
 if !result.OK {if result.Error.Message==""{result.Error.Message="La API rechazó la solicitud"};return result,errors.New(result.Error.Message)}
 return result,nil
}
