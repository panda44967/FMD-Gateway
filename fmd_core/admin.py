from django.contrib import admin
from .models import Supplier, SupplierPart, HomogeneousMaterial, SubstanceDeclaration, RegulatoryRule, ReviewTask

class SubstanceInline(admin.TabularInline):
    model = SubstanceDeclaration
    extra = 0
    fields = ('cas', 'concentration_pct', 'pfas_intentional_use', 'evidence_status', 'rohs_eval', 'reach_eval', 'pfas_eval')
    readonly_fields = ('rohs_eval', 'reach_eval', 'pfas_eval')


class MaterialInline(admin.StackedInline):
    model = HomogeneousMaterial
    extra = 0
    fields = ('material_id', 'name', 'mass_g', 'total_concentration_pct', 'mass_balance_valid')
    readonly_fields = ('total_concentration_pct', 'mass_balance_valid')


class ReviewTaskInline(admin.TabularInline):
    model = ReviewTask
    extra = 0
    fields = ('severity', 'title', 'remediation_instruction', 'is_resolved')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'supplier_code', 'contact_email', 'quality_score', 'created_at')
    search_fields = ('name', 'supplier_code')


@admin.register(SupplierPart)
class SupplierPartAdmin(admin.ModelAdmin):
    list_display = ('part_number', 'supplier', 'fmd_tier', 'rohs_status', 'reach_status', 'pfas_status', 'overall_status', 'updated_at')
    list_filter = ('overall_status', 'fmd_tier', 'rohs_status', 'reach_status', 'pfas_status')
    search_fields = ('part_number', 'part_name')
    inlines = [MaterialInline, ReviewTaskInline]


@admin.register(HomogeneousMaterial)
class HomogeneousMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'material_id', 'part', 'mass_g', 'total_concentration_pct', 'mass_balance_valid')
    list_filter = ('mass_balance_valid',)
    search_fields = ('name', 'material_id', 'part__part_number')
    inlines = [SubstanceInline]


@admin.register(SubstanceDeclaration)
class SubstanceDeclarationAdmin(admin.ModelAdmin):
    list_display = ('cas', 'name', 'material', 'concentration_pct', 'pfas_intentional_use', 'evidence_status', 'rohs_eval')
    list_filter = ('rohs_eval', 'reach_eval', 'pfas_eval', 'pfas_intentional_use')
    search_fields = ('cas', 'name', 'material__name')


@admin.register(RegulatoryRule)
class RegulatoryRuleAdmin(admin.ModelAdmin):
    list_display = ('substance_name', 'cas', 'regulation', 'version', 'threshold_pct', 'is_svhc', 'is_pfas', 'is_active')
    list_filter = ('regulation', 'version', 'is_active', 'is_svhc', 'is_pfas')
    search_fields = ('substance_name', 'cas')


@admin.register(ReviewTask)
class ReviewTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'part', 'severity', 'is_resolved', 'created_at')
    list_filter = ('severity', 'is_resolved')
    search_fields = ('title', 'part__part_number', 'remediation_instruction')
