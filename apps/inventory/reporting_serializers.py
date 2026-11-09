from rest_framework import serializers


class StockStatusSerializer(serializers.Serializer):
    facility_id = serializers.UUIDField()
    facility_code = serializers.CharField()
    facility_name = serializers.CharField()

    organization_id = serializers.UUIDField()

    medicine_id = serializers.UUIDField()
    medicine_code = serializers.CharField()
    medicine_name = serializers.CharField()

    on_hand = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    reserved = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    available = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    amc = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    months_of_stock = serializers.CharField(
        allow_null=True,
    )

    batch_count = serializers.IntegerField()

    status = serializers.CharField()


class ExpiryReportSerializer(serializers.Serializer):
    facility_id = serializers.UUIDField()
    facility_name = serializers.CharField()

    medicine_id = serializers.UUIDField()
    medicine_code = serializers.CharField()
    medicine_name = serializers.CharField()

    batch_id = serializers.UUIDField()
    batch_number = serializers.CharField()

    expiry_date = serializers.DateField()
    days_until_expiry = serializers.IntegerField()

    on_hand = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    reserved = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    available = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
    )

    status = serializers.CharField()


class StockDashboardSummarySerializer(serializers.Serializer):
    facilities_reporting = serializers.IntegerField()
    medicine_facility_records = serializers.IntegerField()

    stockout_count = serializers.IntegerField()
    critical_stock_count = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    adequate_stock_count = serializers.IntegerField()
    high_coverage_count = serializers.IntegerField()
    no_consumption_history_count = serializers.IntegerField()

    expired_batch_count = serializers.IntegerField()
    near_expiry_batch_count = serializers.IntegerField()