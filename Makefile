PYTHON ?= python3
FONTFORGE ?= fontforge
SOURCE_URL ?= https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip
DOWNLOAD_DIR ?= vendor/downloads
SOURCE_DIR ?= vendor/source
OUTPUT_DIR ?= instance_otf
BUILD_FLAGS ?=
PACKAGE_NAME ?= SNUEdgeSans
PACKAGE_DIR ?= dist/$(PACKAGE_NAME)
PACKAGE_ZIP ?= dist/$(PACKAGE_NAME).zip

.PHONY: build test package clean

build:
	$(FONTFORGE) -lang=py -script scripts/build_snu_edge_sans.py \
		--source-url "$(SOURCE_URL)" \
		--download-dir "$(DOWNLOAD_DIR)" \
		--source-dir "$(SOURCE_DIR)" \
		--output-dir "$(OUTPUT_DIR)" \
		$(BUILD_FLAGS)

test:
	$(PYTHON) -m unittest discover -s tests

package: build
	rm -rf dist
	mkdir -p "$(PACKAGE_DIR)"
	cp LICENSE README.md "$(PACKAGE_DIR)/"
	cp "$(OUTPUT_DIR)"/SNUEdgeSans-*.otf "$(PACKAGE_DIR)/"
	cd dist && zip -qr "$(PACKAGE_NAME).zip" "$(PACKAGE_NAME)"
	test -f "$(PACKAGE_ZIP)"

clean:
	rm -rf instance_otf vendor dist
