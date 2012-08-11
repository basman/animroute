# this makefile is for huge animroute projects with many conf files

# prevent an accidentially existing file "all" from inhibiting all: above
.PHONY: all

# this only triggers make for old avi files, not for new conf files
all:
	for f in day_*.conf; do \
		g=$${f%.conf}.avi; \
		$(MAKE) $$g; \
	done

%.avi: %.conf
	./animroute.py $<
