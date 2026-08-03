include ../../../_lesson.mk

# CrewAI drags in libraries that register pytest plugins, and one of them
# rewrites assertions in a way that turns a skip into a collection error. The
# lesson needs no plugin beyond pytest itself, so it loads none.
export PYTEST_DISABLE_PLUGIN_AUTOLOAD = 1
