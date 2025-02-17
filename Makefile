.PHONY:
	ui
	clean

ui: $(patsubst %.ui, %_ui.py, $(wildcard *.ui))

%_ui.py: %.ui
	pyuic5 $< -o $@
	awk -i inplace '{ \
		if (match($$0, /QtCore\.Qt\.Qt::(\w+)::(\w+)/, arr)) { \
			gsub(/QtCore\.Qt\.Qt::(\w+)::(\w+)/, "QtCore.Qt." arr[1] "." arr[2]); \
		} \
		print \
	}' $@
	awk -i inplace '{ \
		if (match($$0, /QtCore\.Qt\.QAction::(\w+)::(\w+)/, arr)) { \
			gsub(/QtCore\.Qt\.QAction::(\w+)::(\w+)/, "QtWidgets.QAction." arr[1] "." arr[2]); \
		} \
		print \
	}' $@
	awk -i inplace '{ \
		if (match($$0, /QtCore\.Qt\.QSizePolicy::(\w+)::(\w+)/, arr)) { \
			gsub(/QtCore\.Qt\.QSizePolicy::(\w+)::(\w+)/, "QtWidgets.QSizePolicy." arr[1] "." arr[2]); \
		} \
		print \
		}' $@
	awk -i inplace '{ \
		if (match($$0, /QtCore\.Qt\.QLayout::(\w+)::(\w+)/, arr)) { \
			gsub(/QtCore\.Qt\.QLayout::(\w+)::(\w+)/, "QtWidgets.QLayout." arr[1] "." arr[2]); \
		} \
		print \
	}' $@

clean:
	rm -f *_ui.py
