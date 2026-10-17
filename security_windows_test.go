//go:build windows

package main
import("bytes";"os";"path/filepath";"testing")
func TestDPAPI(t *testing.T){
 secret:=[]byte("local-test-secret")
 encrypted,err:=protect(secret);if err!=nil{t.Fatal(err)}
 if bytes.Contains(encrypted,secret){t.Fatal("plaintext on disk")}
 plain,err:=unprotect(encrypted);if err!=nil || !bytes.Equal(secret,plain){t.Fatal("roundtrip failed",err)}
 if _,err=unprotect([]byte("corrupt"));err==nil{t.Fatal("accepted corrupt data")}
}
func TestAtomicReplace(t *testing.T){
 dir:=t.TempDir();source:=filepath.Join(dir,"tmp");dest:=filepath.Join(dir,"config")
 os.WriteFile(source,[]byte("new"),0600);os.WriteFile(dest,[]byte("old"),0600)
 if err:=replaceConfig(source,dest);err!=nil{t.Fatal(err)}
 value,_:=os.ReadFile(dest);if string(value)!="new"{t.Fatal("not replaced")}
}
