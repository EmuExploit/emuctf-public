package main

import (
	"github.com/fatduck/duckduckgo/models"
	_ "github.com/fatduck/duckduckgo/routes"

	beego "github.com/beego/beego/v2/server/web"
)

func main() {
	models.InitialiseAdmin()
	beego.Run()
}
