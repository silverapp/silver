local Pipeline(python_version, django_version) = {
    "kind": "pipeline",
    "name": "python:" + python_version + ",django" + django_version,
    "platform": {
        "os": "linux",
        "arch": "amd64"
    },
    "steps": [
        {
            "name": "test",
            "pull": "always",
            "image": "python:" + python_version,
            "commands": [
                "make dependencies",
                "pip install -U \"Django" + django_version + "\"",
                "mkdir /var/log/silver",
                "make lint",
                "make test"
            ],
            "settings": {
                "group": "build"
            },
            "environment": {
                "SILVER_DB_URL": "mysql://silver:silver@mysql/db"
            }
        },
        {
            "name": "publish-docker",
            "pull": "if-not-exists",
            "image": "plugins/docker",
            "settings": {
                "force_tag": true,
                "group": "publish",
                "repo": "presslabs/silver",
                "tags": [
                    "${DRONE_BRANCH/master/latest}",
                    "${DRONE_COMMIT_SHA:0:7}"
                ],
                "username": "_json_key",
                "password": {
                    "from_secret": "DOCKERHUB_CONFIG_JSON"
                }
            },
            "when": {
                "event": [
                    "push",
                    "tag"
                ],
                "branch": [
                    "master"
                ]
            }
        },
        {
            "name": "trigger-docs-build",
            "pull": "if-not-exists",
            "image": "plugins/downstream",
            "settings": {
                "fork": true,
                "repositories": [
                    "presslabs/docs"
                ],
                "server": "https://drone.presslabs.net"
            },
            "environment": {
                "DRONE_TOKEN": {
                    "from_secret": "DRONE_TOKEN"
                }
            },
            "when": {
                "branch": [
                    "master"
                ],
                "event": [
                    "push"
                ]
            }
        }
    ],
    "services": [
        {
            "name": "mysql",
            "pull": "if-not-exists",
            "image": "mysql:5.7",
            "environment": {
                "MYSQL_DATABASE": "test_db",
                "MYSQL_PASSWORD": "silver",
                "MYSQL_ROOT_PASSWORD": "secret",
                "MYSQL_USER": "silver"
            },
            "command": [
                "--character-set-server=utf8mb4"
            ]
        },
        {
            "name": "redis",
            "pull": "if-not-exists",
            "image": "redis:3-alpine"
        }
    ]
};

[
    Pipeline("3.7", ">=3.1,<3.2"),
    Pipeline("3.8", ">=3.1,<3.2"),
    Pipeline("3.7", ">=3.2,<3.3"),
    Pipeline("3.8", ">=3.2,<3.3"),
]
