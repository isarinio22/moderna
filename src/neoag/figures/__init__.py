"""Static figure rendering.

Matplotlib with the Agg backend, so figures build identically on a laptop and in
CI with no browser involved. The website draws its own interactive versions in
SVG; these are the static exports used in the README, the LinkedIn assets, and
anywhere an image has to stand on its own.
"""

import matplotlib

matplotlib.use("Agg")
