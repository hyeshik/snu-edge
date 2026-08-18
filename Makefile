PYTHON ?= python3
FONTFORGE ?= fontforge
TYPST ?= typst
SOURCE_URL ?= https://campaign.naver.com/nanumsquare_neo/download/NaverNanumSquare.zip
DOWNLOAD_DIR ?= vendor/downloads
SOURCE_DIR ?= vendor/source
OUTPUT_DIR ?= instance_otf
MONTSERRAT_DIR ?= vendor/montserrat
V1_REFERENCE_DIR ?= proof/generated/v1_otf
BUILD_FLAGS ?=
PACKAGE_VERSION ?= 0.3.1
PACKAGE_NAME ?= SNUEdge-$(PACKAGE_VERSION)
PACKAGE_DIR ?= dist/$(PACKAGE_NAME)
PACKAGE_ZIP ?= dist/$(PACKAGE_NAME).zip
PROOF_SOURCE ?= proof/montserrat-proof.typ
PROOF_PDF ?= proof/SNUEdge-Montserrat-Proof.pdf
LONG_PROOF_SOURCE ?= proof/long-text-proof.typ
LONG_PROOF_PDF ?= proof/SNUEdge-Montserrat-LongText-Proof.pdf
SPACING_AUDIT ?= proof/generated/montserrat-spacing-audit.json
H_WEIGHT_AUDIT ?= proof/generated/h-stroke-weight-audit.json
H_WEIGHT_IMAGE_PREFIX ?= proof/generated/h-stroke-weight-audit

.PHONY: build montserrat v1-reference test verify package spacing-audit weight-audit proof long-proof clean

build: montserrat
	$(FONTFORGE) -lang=py -script scripts/build_snu_edge.py \
		--source-url "$(SOURCE_URL)" \
		--download-dir "$(DOWNLOAD_DIR)" \
		--source-dir "$(SOURCE_DIR)" \
		--montserrat-dir "$(MONTSERRAT_DIR)" \
		--output-dir "$(OUTPUT_DIR)" \
		$(BUILD_FLAGS)

montserrat:
	$(PYTHON) scripts/fetch_montserrat.py --output-dir "$(MONTSERRAT_DIR)"

verify: build
	$(PYTHON) scripts/verify_snu_edge.py --font-dir "$(OUTPUT_DIR)"

v1-reference:
	$(FONTFORGE) -lang=py -script scripts/build_v1_reference.py \
		--source-url "$(SOURCE_URL)" \
		--download-dir "$(DOWNLOAD_DIR)" \
		--source-dir "$(SOURCE_DIR)" \
		--output-dir "$(V1_REFERENCE_DIR)"

test:
	$(PYTHON) -m unittest discover -s tests

spacing-audit: montserrat
	test -f "$(MONTSERRAT_DIR)/Montserrat-VariableFont_wght.ttf"
	test -f "$(MONTSERRAT_DIR)/Montserrat-Italic-VariableFont_wght.ttf"
	$(PYTHON) scripts/audit_montserrat_spacing.py \
		--font-dir "$(MONTSERRAT_DIR)" \
		--output "$(SPACING_AUDIT)"

weight-audit: v1-reference montserrat
	test -f "$(MONTSERRAT_DIR)/Montserrat-VariableFont_wght.ttf"
	$(PYTHON) scripts/audit_h_stroke_weights.py \
		--edge-dir "$(V1_REFERENCE_DIR)" \
		--montserrat "$(MONTSERRAT_DIR)/Montserrat-VariableFont_wght.ttf" \
		--montserrat-italic "$(MONTSERRAT_DIR)/Montserrat-Italic-VariableFont_wght.ttf" \
		--output "$(H_WEIGHT_AUDIT)" \
		--image-prefix "$(H_WEIGHT_IMAGE_PREFIX)"

proof: build spacing-audit weight-audit
	mkdir -p "$(dir $(PROOF_PDF))"
	$(TYPST) compile \
		--font-path "$(MONTSERRAT_DIR)" \
		--font-path "$(V1_REFERENCE_DIR)" \
		--font-path "$(OUTPUT_DIR)" \
		"$(PROOF_SOURCE)" \
		"$(PROOF_PDF)"

long-proof: build
	mkdir -p "$(dir $(LONG_PROOF_PDF))"
	$(TYPST) compile \
		--font-path "$(MONTSERRAT_DIR)" \
		--font-path "$(OUTPUT_DIR)" \
		"$(LONG_PROOF_SOURCE)" \
		"$(LONG_PROOF_PDF)"

package: verify
	rm -rf dist
	mkdir -p "$(PACKAGE_DIR)"
	cp LICENSE README.md requirements.txt "$(PACKAGE_DIR)/"
	cp "$(OUTPUT_DIR)"/SNUEdge-*.otf "$(PACKAGE_DIR)/"
	cd dist && zip -qr "$(PACKAGE_NAME).zip" "$(PACKAGE_NAME)"
	test -f "$(PACKAGE_ZIP)"

clean:
	rm -rf "$(V1_REFERENCE_DIR)"
	rm -rf instance_otf vendor dist
	rm -f "$(PROOF_PDF)"
	rm -f "$(LONG_PROOF_PDF)"
	rm -f "$(SPACING_AUDIT)"
	rm -f "$(H_WEIGHT_AUDIT)"
	rm -f "$(H_WEIGHT_IMAGE_PREFIX)"-*.png
