from rest_framework import serializers

from .models import InvestorProfile, SavedItem


class InvestorPublicProfileSerializer(serializers.ModelSerializer):
    investments_count = serializers.SerializerMethodField()
    saved_startups_count = serializers.SerializerMethodField()

    class Meta:
        model = InvestorProfile
        fields = [
            'id',
            'company_name',
            'bio',
            'investment_focus',
            'website',
            'investments_count',
            'saved_startups_count',
            'created_at',
        ]

    def get_investments_count(self, obj):
        return obj.investment_set.count()

    def get_saved_startups_count(self, obj):
        return obj.savedstartup_set.count()


class InvestorProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestorProfile
        fields = ['company_name', 'bio', 'investment_focus', 'website']


class SavedItemCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=['company', 'startup', 'project'])
    target_id = serializers.CharField(max_length=50)


class SavedItemResponseSerializer(serializers.ModelSerializer):
    saved_id = serializers.IntegerField(source='id')

    class Meta:
        model = SavedItem
        fields = ['saved_id', 'saved_at']
