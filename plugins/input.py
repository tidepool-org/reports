import pluginlib

@pluginlib.Parent('input')
class InputSource():
    key = pluginlib.abstractattribute

    def __init__(self, config: dict):
        self.config = config
