package middleware

import (
	"github.com/beego/beego/v2/server/web/context"
	"github.com/fatduck/duckduckgo/constants"
	"github.com/fatduck/duckduckgo/services"
)

func AuthMiddleware(ctx *context.Context) {
	uname, ok := ctx.Input.Session(constants.SessionKey).(string)
	if !ok {
		ctx.Redirect(302, "/login")
		return
	}
	_, err := services.GetUser(uname)
	if err != nil {
		ctx.Output.Session(constants.SessionKey, nil)
		ctx.Redirect(302, "/login")
	}
}
