# 1.2 Token & cost meter

Count before you send (vendor counter), measure after from the `usage` object.
Fill the TODOs in `src/meter.py`. Key ideas: tiktoken undercounts Claude; cached
tokens are ~10% price; reasoning tokens bill as output.
