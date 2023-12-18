# generate python virtual environment and install packages
env:
	python3 -m venv .env
	while [[ !(-d ".env") ]] ; do \
		echo "waiting for virtual environment to be created" ; \
		sleep 1 ; \
	done; \
	source .env/bin/activate; \
	pip3 install -r requirements.txt
