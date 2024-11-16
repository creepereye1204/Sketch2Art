.PHONY: prod
run:
	supervisorctl start app

.PHONY: dev
run:
	python3 app.py

