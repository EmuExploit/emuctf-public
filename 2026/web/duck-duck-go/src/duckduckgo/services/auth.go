package services

import (
	"errors"
	"regexp"

	"github.com/beego/beego/v2/client/orm"
	"github.com/fatduck/duckduckgo/models"
)

func Register(username string, password string, confirm string) (errs []string) {
	if password != confirm {
		errs = append(errs, "Passwords do not match.")
	}

	match, err := regexp.MatchString("^[a-zA-Z0-9_-]*$", username)
	if !match || err != nil {
		errs = append(errs, "Invalid username, must match ^[a-zA-Z0-9_-]*$")
	}

	if UserExists(username) {
		errs = append(errs, "User exists")
	}

	if len(errs) > 0 {
		return errs
	}

	u := models.User{Username: username, Password: password}
	o := orm.NewOrm()
	_, err = o.Insert(&u)
	if err != nil {
		return []string{"Error registering user"}
	}
	return []string{}
}

func Authenticate(username string, password string) (err error) {
	u, err := GetUser(username)
	if err != nil {
		return errors.New("Invalid username or password")
	}
	if password != u.Password {
		return errors.New("Invalid username or password")
	}
	return nil
}
