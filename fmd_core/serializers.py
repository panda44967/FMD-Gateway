from rest_framework import serializers
from .models import Supplier, SupplierPart, PartRevision, HomogeneousMaterial, SubstanceDeclaration, RegulatoryRule, ReviewTask

class PartRevisionSerializer(serializers.ModelSerializer):
    formatted_created_at = serializers.SerializerMethodField()

    class Meta:
        model = PartRevision
        fields = '__all__'

    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')


class SubstanceDeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstanceDeclaration
        fields = '__all__'


class HomogeneousMaterialSerializer(serializers.ModelSerializer):
    substances = SubstanceDeclarationSerializer(many=True, read_only=True)

    class Meta:
        model = HomogeneousMaterial
        fields = '__all__'


class ReviewTaskSerializer(serializers.ModelSerializer):
    part_number = serializers.CharField(source='part.part_number', read_only=True)
    material_name = serializers.CharField(source='material.name', read_only=True, default='')

    class Meta:
        model = ReviewTask
        fields = '__all__'


class SupplierPartSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default='')
    supplier_code = serializers.CharField(source='supplier.supplier_code', read_only=True, default='')
    materials = HomogeneousMaterialSerializer(many=True, read_only=True)
    review_tasks = ReviewTaskSerializer(many=True, read_only=True)
    revisions = PartRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierPart
        fields = '__all__'


class RegulatoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulatoryRule
        fields = '__all__'
