# Copyright 2020 Javier de las Heras <jheras@alquemy.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    extract = fields.Float(
        string="Extracto SILICIE",
    )

    def _action_done(self):
        move = super(StockMove, self)._action_done()
        move.generate_silicie_fields()
        return move

    @api.multi
    def generate_silicie_fields(self):
        super().generate_silicie_fields()
        for move in self:
            if move.send_silicie:
                continue
            is_silicie_move = False
            if move.product_id.product_tmpl_id.silicie_product_type == "none":
                continue
            # Production
            if move.location_id.usage == "production" and \
                    move.location_dest_id.usage == "internal":
                is_silicie_move = True
                move.silicie_proof_type_id = self.env.ref(
                    "l10n_es_aeat_silicie.aeat_proof_type_silicie_j09")
                move.silicie_move_type_id = self.env.ref(
                    "l10n_es_aeat_silicie.aeat_move_type_silicie_a15")
                if not move.silicie_operation_num:
                    move.silicie_operation_num = self.env[
                        "ir.sequence"].next_by_code("silicie.operation")
                move.silice_tax_position = "1"
                move.silicie_processing_id = \
                    move.production_id.routing_id.silicie_processing_id
            # Production BoM
            elif move.location_id.usage == "internal" and \
                    move.location_dest_id.usage == "production":
                is_silicie_move = True
                move.silicie_proof_type_id = self.env.ref(
                    "l10n_es_aeat_silicie.aeat_proof_type_silicie_j09")
                move.silicie_move_type_id = self.env.ref(
                    "l10n_es_aeat_silicie.aeat_move_type_silicie_a14")
                if not move.silicie_operation_num:
                    move.silicie_operation_num = self.env[
                        "ir.sequence"].next_by_code("silicie.operation")
                move.silice_tax_position = "1"
                move.silicie_processing_id = move.production_id\
                    .routing_id.silicie_processing_id
            # Loss
            elif move.location_id.usage == "internal" and \
                    move.location_dest_id.usage == "inventory" and \
                    move.location_dest_id.scrap_location:
                is_silicie_move = True
                move.silicie_proof_type_id = self.env.ref(
                    "l10n_es_aeat_silicie.aeat_proof_type_silicie_j11")
                move.silice_tax_position = "1"
                if move.scrap_ids:
                    move.notes_silice = move.scrap_ids[:1].origin
                # Elaboración AD02
                if move.scrap_ids[:1].scrap_type == "processing":
                    move.silicie_move_type_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_move_type_silicie_a32")
                    move.silicie_loss_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_loss_silicie_ad02")
                # Embotellado AD12
                elif move.scrap_ids[:1].scrap_type == "bottling":
                    move.silicie_move_type_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_move_type_silicie_a32")
                    move.silicie_loss_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_loss_silicie_ad12")
                # Compras AD15
                elif move.scrap_ids[:1].scrap_type == "reception":
                    move.silicie_move_type_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_move_type_silicie_a30")
                    move.silicie_loss_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_loss_silicie_ad15")
                else:
                    move.silicie_move_type_id = self.env.ref(
                        "l10n_es_aeat_silicie.aeat_move_type_silicie_a28")
            if is_silicie_move:
                move.silicie_product_type = \
                    move.product_id.product_tmpl_id.silicie_product_type
                move.factor_conversion_silicie = \
                    move.product_id.product_tmpl_id.factor_conversion_silicie
                move.alcoholic_grade = \
                    move.product_id.product_tmpl_id.alcoholic_grade
                move.nc_code = move.product_id.product_tmpl_id.nc_code
                move.product_key_silicie_id = \
                    move.product_id.product_tmpl_id.product_key_silicie_id
                move.container_type_silicie_id = \
                    move.product_id.product_tmpl_id.container_type_silicie_id
                move.epigraph_silicie_id = \
                    move.product_id.product_tmpl_id.epigraph_silicie_id
                move.uom_silicie_id = \
                    move.product_id.product_tmpl_id.uom_silicie_id
                move.fiscal_position_id = \
                    move.picking_id.partner_id.property_account_position_id
                # Check if all fields have been correctly generated
                move.check_silicie_fields()

    @api.multi
    def _get_data_dict(self, lot):
        self.ensure_one()
        Lots = self.env["stock.production.lot"]
        a14_type = self.env.ref(
            "l10n_es_aeat_silicie.aeat_move_type_silicie_a14")
        data = super()._get_data_dict(lot)
        if self.product_id.silicie_product_type == "beer":
            data["qty_done"] = lot["qty_done"]
            if self.product_id.product_class == "raw":
                lot_id = Lots.browse(lot["lot_id"])
                data["extract"] = lot_id.extract or ""
                if self.silicie_move_type_id == a14_type:
                    if data["extract"]:
                        data["kg_extract"] = \
                            data["extract"] * data["qty_done"] / 100
                    else:
                        data["kg_extract"] = ""
                if self.product_id.product_class == "manufactured":
                    density = lot_id.density
                    data["alcoholic_grade"] = ""
                    data["density"] = density
                    data["grado_plato"] = density * 1000 - 1000 / 4
            if not data['container_code']:
                data["qty_done"] = ""
        return data

    @api.multi
    def _prepare_values(self, lot):
        self.ensure_one()
        data = self._get_data_dict(lot)
        values = super()._prepare_values(lot)
        values.update({
            "Porcentaje de Extracto": data.get("extract", ""),
            "Kg. - Extracto": data.get("kg_extract", ""),
            "Grado Alcohólico": data.get("alcoholic_grade", ""),
            "Densidad": data.get("density", ""),
            "Grado Plato Medio": data.get("grado_plato", ""),
        })
        return values

    @api.multi
    def _get_move_fields(self):
        self.ensure_one()
        values = super()._get_move_fields()
        values.update({
            'extract': self.extract,
        })
        return values