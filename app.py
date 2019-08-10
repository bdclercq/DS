from flask import Flask
from DS.API.api import api
from DS.Site.site import site

app = Flask(__name__)
app.register_blueprint(api)
app.register_blueprint(site)

if __name__ == "__main__":
    app.run()
