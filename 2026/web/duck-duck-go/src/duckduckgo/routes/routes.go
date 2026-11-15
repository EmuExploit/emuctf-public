package routes

func init() {
	registerUnauthRoutes()
	registerAuthRoutes()
	registerSubscriberRoutes()
	registerAdminRoutes()
}
