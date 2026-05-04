import sys
import os
import ast
import pathlib
from pathlib import Path
import networkx as nx
from pyvis.network import Network

# Suppress warnings for Syntax
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Print the current working directory to verify that the script is being run from the correct location.
cwd = os.getcwd()
# print(cwd) # Helper line to check that the current working directory is correct.

# Set path to repo, which you are doing architecture recovery on.
CODE_ROOT_FOLDER = "../zeeguu-api/"
# print(CODE_ROOT_FOLDER) # Helper line to check that path prints correctly

# Helper function to get the full path of a file in the codebase, given its relative path from the root of the codebase.
def file_path(file_name):
  return CODE_ROOT_FOLDER+file_name

# Assertion to check that the file_path function is working correctly. If the assertion fails, it will raise an AssertionError.
assert (file_path("zeeguu/core/model/user.py") == "../zeeguu-api/zeeguu/core/model/user.py")

# Helper function to convert a file path to a module name.
def module_name_from_file_path(full_path):
  file_name = full_path[len(CODE_ROOT_FOLDER):]
  file_name = file_name.replace("/__init__.py", "")
  file_name = file_name.replace("/", ".")
  file_name = file_name.replace(".py", "")
  return file_name

# Assertion to check that the module_name_from_file_path function is working correctly. If the assertion fails, it will raise an AssertionError.
assert 'zeeguu.core.model.user' == module_name_from_file_path(file_path('zeeguu/core/model/user.py'))


# Helper function to check if a module is in a given package.
def in_package(module_name, package_prefix):
  return (
    module_name == package_prefix
    or module_name.startswith(package_prefix + ".")
  )


def package_of(module_name, depth=3):
  """
  Convert a module name to a package name at a given depth.
  Example:
    zeeguu.core.model.user -> zeeguu.core.model
  """
  return ".".join(module_name.split(".")[:depth])

# Use ast to find imports
def imports_from_file(file_path):
  imports = []

  with open(file_path, encoding="utf-8", errors="ignore") as f:
    tree = ast.parse(f.read(), filename=file_path)

  for node in ast.walk(tree):
    # import x, y, z
    if isinstance(node, ast.Import):
      for name in node.names:
        imports.append(name.name)

    # from x import y, z
    elif isinstance(node, ast.ImportFrom):
      if node.module is not None:
        imports.append(node.module)
      else:
        # handles: from . import y
        imports.append(".")

  return imports

imports_from_file(file_path('zeeguu/core/model/user.py'))

# test
bookmark_imports = imports_from_file(file_path('zeeguu/core/model/bookmark.py'))
unique_code_imports =  imports_from_file(file_path('zeeguu/core/model/unique_code.py'))
print(bookmark_imports)
print(unique_code_imports)
assert(unique_code_imports != bookmark_imports)

# Plot
# a function to draw a graph
def draw_graph(G, figure_name, height="900px", width="100%", notebook=False):
  """
  Draw a directed graph using PyVis and save it as an interactive HTML file.
  Edge A -> B means A imports B.
  """

  os.makedirs("./graphs", exist_ok=True)

  net = Network(
    height=height,
    width=width,
    directed=True,
    notebook=notebook,
    bgcolor="#ffffff",
    font_color="#000000",
  )

  # Optional physics layout settings
  net.barnes_hut(
    gravity=-30000,
    central_gravity=0.3,
    spring_length=200,
    spring_strength=0.05,
    damping=0.09,
    overlap=0,
  )

  # Add nodes
  for node in G.nodes:
    net.add_node(
      node,
      label=node,
      title=node,
    )

  # Add edges
  for source, target in G.edges:
    net.add_edge(
      source,
      target,
      title=f"{source} imports {target}",
    )

  # Add interaction buttons
  net.show_buttons(filter_=["physics"])

  output_path = f"./graphs/{figure_name}.html"
  net.write_html(output_path)

  print(f"Saved interactive graph to: {output_path}")


# Make a directed graph of dependencies, where an edge from A to B means that A imports B.
def dependencies_digraph(code_root_folder):
  files = Path(code_root_folder).rglob("*.py")

  G = nx.DiGraph()

  for file in files:
    file_path = str(file)

    source_module = module_name_from_file_path(file_path)

    if source_module not in G.nodes:
      G.add_node(source_module)

    for target_module in imports_from_file(file_path):
      if target_module.startswith("zeeguu"):
        G.add_edge(source_module, target_module)
      # print(module_name + "=>" + each + ".")

  return G

# Make a directed graph of dependencies, where an edge from A to B means that A imports B, but only at the package level 
# (i.e. zeeguu.core.model.user imports zeeguu.core.model.bookmark would be represented as zeeguu.core.model -> zeeguu.core.model).
def package_dependencies_digraph(code_root_folder, depth=3):
  files = Path(code_root_folder).rglob("*.py")
  G = nx.DiGraph()

  for file in files:
    source_module = module_name_from_file_path(str(file))

    if not source_module.startswith("zeeguu"):
      continue

    source_pkg = package_of(source_module, depth)
    G.add_node(source_pkg)

    for target_module in imports_from_file(str(file)):
      if target_module.startswith("zeeguu"):
        target_pkg = package_of(target_module, depth)
        if source_pkg != target_pkg:
          G.add_edge(source_pkg, target_pkg)

  return G

# Creating dependency graphs at different levels of granularity and saving them as interactive HTML files.
DG_3 = package_dependencies_digraph(CODE_ROOT_FOLDER)
draw_graph(DG_3, "architecture-packages")

DG_2 = package_dependencies_digraph(CODE_ROOT_FOLDER, depth=2)
draw_graph(DG_2, "architecture-packages-depth-2")

DG_4 = package_dependencies_digraph(CODE_ROOT_FOLDER, depth=4)
draw_graph(DG_4, "architecture-packages-depth-4")

# Sub graphs of specific packages
# Core package, which contains the main domain logic of the application, including models, services, and repositories.
DG_core = DG_3.subgraph(
  [n for n in DG_3.nodes if n.startswith("zeeguu.core")]
)
draw_graph(DG_core, "architecture-packages-core")

DG_model = DG_4.subgraph(
  [n for n in DG_4.nodes if n.startswith("zeeguu.core.model")]
) 
draw_graph(DG_model, "architecture-packages-core-model")