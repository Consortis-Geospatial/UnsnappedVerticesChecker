def classFactory(iface):
    from .plugin import VertexProximityPlugin
    return VertexProximityPlugin(iface)
