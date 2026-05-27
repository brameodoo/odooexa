<odoo>
    <!-- Menú Principal -->
    <menuitem id="menu_sgs_root" name="SGS Custodias" web_icon="sgs_custody_perdiem,static/description/icon.png" sequence="10" groups="group_sgs_manager"/>

    <!-- Categorías -->
    <menuitem id="menu_sgs_operations" name="Operaciones" parent="menu_sgs_root" sequence="10"/>
    <menuitem id="menu_sgs_finance" name="Finanzas" parent="menu_sgs_root" sequence="20"/>
    <menuitem id="menu_sgs_config" name="Configuración" parent="menu_sgs_root" sequence="100"/>

    <!-- Acciones -->
    <record id="action_sgs_custodian" model="ir.actions.act_window">
        <field name="name">Custodios</field>
        <field name="res_model">sgs.custodian</field>
        <field name="view_mode">kanban,list,form</field>
    </record>

    <record id="action_sgs_route_service" model="ir.actions.act_window">
        <field name="name">Servicios y Gastos</field>
        <field name="res_model">sgs.route.service</field>
        <field name="view_mode">list,form</field>
    </record>

    <record id="action_sgs_perdiem_deposit" model="ir.actions.act_window">
        <field name="name">Depósitos de Viáticos</field>
        <field name="res_model">sgs.perdiem.deposit</field>
        <field name="view_mode">list,form</field>
    </record>

    <record id="action_sgs_fiscal_receipt" model="ir.actions.act_window">
        <field name="name">Comprobantes Fiscales</field>
        <field name="res_model">sgs.fiscal.receipt</field>
        <field name="view_mode">list,form</field>
    </record>

    <record id="action_sgs_vehicle" model="ir.actions.act_window">
        <field name="name">Vehículos</field>
        <field name="res_model">sgs.vehicle</field>
        <field name="view_mode">list,form</field>
    </record>

    <record id="action_sgs_client" model="ir.actions.act_window">
        <field name="name">Clientes</field>
        <field name="res_model">sgs.client</field>
        <field name="view_mode">list,form</field>
    </record>

    <!-- Menús de Operaciones -->
    <menuitem id="menu_sgs_custodian" name="Custodios" parent="menu_sgs_operations" action="action_sgs_custodian" sequence="10"/>
    <menuitem id="menu_sgs_route_service" name="Servicios / Gastos" parent="menu_sgs_operations" action="action_sgs_route_service" sequence="20"/>

    <!-- Menús de Finanzas -->
    <menuitem id="menu_sgs_perdiem_deposit" name="Depósitos" parent="menu_sgs_finance" action="action_sgs_perdiem_deposit" sequence="10"/>
    <menuitem id="menu_sgs_fiscal_receipt" name="Comprobantes Fiscales" parent="menu_sgs_finance" action="action_sgs_fiscal_receipt" sequence="20"/>

    <!-- Menús de Configuración -->
    <menuitem id="menu_sgs_vehicle" name="Vehículos" parent="menu_sgs_config" action="action_sgs_vehicle" sequence="10"/>
    <menuitem id="menu_sgs_client" name="Clientes" parent="menu_sgs_config" action="action_sgs_client" sequence="20"/>
</odoo>
