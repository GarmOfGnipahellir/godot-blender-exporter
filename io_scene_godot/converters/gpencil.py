"""Exports ^2.80 grease pencil strokes"""

import mathutils

from .material import export_material
from ..structures import NodeTemplate
from .utils import MeshResourceKey
from .mesh import (
    ArrayMeshResource,
    Surface,
    Vertex,
    fix_vertex,
    export_object_link_material
)


def export_gpencil_node(escn_file, export_settings, obj, parent_gd_node):
    mesh_node = NodeTemplate(obj.name, "MeshInstance", parent_gd_node)
    mesh_exporter = ArrayMeshResourceExporter(obj)

    mesh_id = mesh_exporter.export_mesh(escn_file, export_settings)

    if mesh_id is not None:
        mesh_node['mesh'] = "SubResource({})".format(mesh_id)
        mesh_node['visible'] = obj.visible_get()

        mesh_resource = escn_file.internal_resources[mesh_id - 1]
        export_object_link_material(
            escn_file, export_settings, obj, mesh_resource, mesh_node
        )

    mesh_node['transform'] = obj.matrix_local

    escn_file.add_node(mesh_node)

    return mesh_node


def vertex_from_stroke_point(point):
    vert = Vertex()
    vert.vertex = fix_vertex(point.co)
    return vert


class ArrayMeshResourceExporter:
    def __init__(self, gpencil_object):
        self.object = gpencil_object

        self.mesh_resource = None

    def export_mesh(self, escn_file, export_settings):
        key = MeshResourceKey('ArrayMesh', self.object, export_settings)
        # Check if mesh resource exists so we don't bother to export it twice,
        mesh_id = escn_file.get_internal_resource(key)
        if mesh_id is not None:
            return mesh_id

        self.mesh_resource = ArrayMeshResource(self.object.name)

        self.generate_surfaces(
            escn_file,
            export_settings,
            self.object.data
        )

        mesh_id = escn_file.add_internal_resource(self.mesh_resource, key)
        assert mesh_id is not None

        return mesh_id

    def generate_surfaces(self, escn_file, export_settings, gpencil):
        surfaces = []

        for layer in gpencil.layers:
            frame = layer.frames[0]
            for stroke in frame.strokes:
                surface_index = len(surfaces)
                self.mesh_resource.set_surface_id(
                    stroke.material_index, surface_index
                )
                surface = Surface()
                surface.id = surface_index
                surface.primitive = 7
                if gpencil.materials:
                    mat = gpencil.materials[stroke.material_index]
                    if (mat is not None and
                            export_settings['material_mode'] != 'NONE'):
                        surface.material = export_material(
                            escn_file,
                            export_settings,
                            self.object,
                            mat
                        )

                for point in stroke.points:
                    new_vert = vertex_from_stroke_point(point)

                    tup = new_vert.get_tup()
                    if tup not in surface.vertex_map:
                        surface.vertex_map[tup] = len(
                            surface.vertex_data.vertices)
                        surface.vertex_data.vertices.append(new_vert)

                surfaces.append(surface)

        for surface in surfaces:
            self.mesh_resource[surface.name_str] = surface
