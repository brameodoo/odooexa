<odoo>
    <!-- En Odoo 19, las categorías se asocian a privilegios y los grupos a privilegios -->
    <record id="module_category_sgs" model="ir.module.category">
        <field name="name">SGS Custodias</field>
        <field name="sequence">30</field>
    </record>

    <!-- Definimos el privilegio (Feature) -->
    <record id="privilege_sgs_manager" model="res.groups.privilege">
        <field name="name">Administrador de Viáticos</field>
        <field name="category_id" ref="module_category_sgs"/>
    </record>

    <!-- Definimos el grupo y le asignamos el privilegio -->
    <record id="group_sgs_manager" model="res.groups">
        <field name="name">Administrador de Viáticos</field>
        <field name="privilege_id" ref="privilege_sgs_manager"/>
        <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    </record>
</odoo>
