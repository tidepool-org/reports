import os
import pluginlib

paths = [ os.path.join(os.path.dirname(__file__), path) for path in [ 'inputs', 'outputs' ] ]
plugin_loader = pluginlib.PluginLoader(paths = paths)
