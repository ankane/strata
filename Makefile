lint:
	pycodestyle strata --ignore=E501

publish: clean
	python3 setup.py bdist_wheel --universal
	ls dist
	# twine upload dist/*
	make clean

clean:
	rm -rf .pytest_cache build dist strata_cli.egg-info
