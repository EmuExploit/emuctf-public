package middleware

import (
	"net/url"

	"github.com/beego/beego/v2/server/web/context"
	"github.com/fatduck/duckduckgo/constants"
)

func AdminMiddleware(ctx *context.Context) {
	AuthMiddleware(ctx)
	username, ok := ctx.Input.Session(constants.SessionKey).(string)
	if !ok {
		ctx.Redirect(302, "/login")
		return
	}

	// only allowing fatduck as admin
	if username != constants.AdminUsername {
		msg := url.QueryEscape("Oi, admins only are allowed on that page!")
		ctx.Redirect(302, "/user/me?error="+msg)
	}
}
