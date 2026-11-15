package services

import (
	"errors"

	"github.com/beego/beego/v2/client/orm"
	"github.com/fatduck/duckduckgo/models"
)

func GetUser(username string) (u *models.User, err error) {
	o := orm.NewOrm()
	u = new(models.User)
	u.Username = username
	err = o.Read(u, "Username")
	if err != nil || u.Id == 0 {
		return nil, errors.New("User does not exists")
	}
	return u, nil
}

func UserExists(username string) (exists bool) {
	_, err := GetUser(username)
	return err == nil
}

func GetUserAndHasSubscribePlan(username string) (u *models.User, issub bool, err error) {
	u, err = GetUser(username)
	if err != nil {
		return nil, false, err
	}
	return u, HasSubscriptionPlan(username), nil
}

func UpdatePassword(username string, origpass string, newpass string) (err error) {
	u, err := GetUser(username)
	if err != nil {
		return errors.New("User does not exist")
	}

	if Authenticate(username, origpass) != nil {
		return errors.New("Incorrect original password")
	}

	u.Password = newpass
	o := orm.NewOrm()
	_, err = o.Update(u)
	return err
}

func DeleteUser(username string) (err error) {
	u, err := GetUser(username)
	if err != nil {
		return errors.New("User does not exist")
	}
	o := orm.NewOrm()
	_, err = o.Delete(u)
	return err
}

func ListUsers() (users *[]models.User, err error) {
	o := orm.NewOrm()

	users = new([]models.User)

	_, err = o.QueryTable(new(models.User)).All(users)
	if err != nil {
		return nil, err
	}

	return users, nil
}
