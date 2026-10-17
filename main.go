package main

import (
 "embed"
 "log"
 "github.com/wailsapp/wails/v2"
 "github.com/wailsapp/wails/v2/pkg/options"
 "github.com/wailsapp/wails/v2/pkg/options/assetserver"
)

//go:embed all:frontend
var assets embed.FS

func main() {
 app := &App{}
 err := wails.Run(&options.App{
  Title: "Primer CRM", Width: 1280, Height: 850, MinWidth: 1000, MinHeight: 700,
  AssetServer: &assetserver.Options{Assets: assets},
  Bind: []interface{}{app},
 })
 if err != nil { log.Fatal(err) }
}
