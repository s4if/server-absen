from flask import Flask, render_template
from flask_migrate import Migrate
from flask.cli import click
from .config import Config
from .model import db, User, Admin
from .seeders import seed_all
from .api import bp as api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

@app.route('/test_layout')
def test_layout():
    return render_template('test.jinja')

# Add CLI command for seeding
@app.cli.command('seed-db')
def seed_db_command():
    """Seed the database with initial data."""
    seed_all()
    click.echo('Database seeded successfully!')

@app.cli.command('reset-admin-password')
@click.option('--username', prompt='Admin username', default='admin')
@click.option('--password', prompt='New admin password', confirmation_prompt=True, hide_input=True)
def reset_admin_password(username, password):
    """Reset admin password."""
    admin = Admin.query.filter_by(username=username).first()
    if admin is None:
        click.echo(f'Admin user {username} not found')
        return
    admin.set_password(password)
    db.session.commit()
    click.echo(f'Admin password for user {username} reset successfully!')

@app.cli.command('reset-user-password')
@click.option('--username', prompt='User username', default='user')
@click.option('--password', prompt='New user password', confirmation_prompt=True, hide_input=True)
def reset_user_password(username, password):
    """Reset regular user password."""
    user = User.query.filter_by(username=username).first()
    if user is None:
        click.echo(f'User {username} not found')
        return
    user.set_password(password)
    db.session.commit()
    click.echo(f'User password for user {username} reset successfully!')

# Register blueprint
app.register_blueprint(api_bp, url_prefix='/api')


if __name__ == '__main__':
    app.run(debug=True)
