from django.test import SimpleTestCase

from apps.redistribution.optimization_engine import (
    optimize_redistribution,
    to_quantity_units,
    to_capacity_limit,
)


class RedistributionOptimizationEngineTests(SimpleTestCase):

    def test_quantity_scaling(self):

        self.assertEqual(
            to_quantity_units("10.500"),
            10500,
        )

    def test_capacity_scaling(self):

        self.assertEqual(
            to_capacity_limit("1.5"),
            1500000,
        )

    def test_single_donor_single_recipient(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "D1",
                    "medicine_id": "M1",
                    "available_quantity": "500",
                    "capacity_per_unit": "0.00001",
                }
            ],
            recipient_needs=[
                {
                    "recipient_id": "R1",
                    "medicine_id": "M1",
                    "shortage_quantity": "300",
                    "priority": "CRITICAL",
                }
            ],
            routes=[
                {
                    "donor_id": "D1",
                    "recipient_id": "R1",
                    "distance_km": "20",
                    "transport_cost_per_capacity_unit": "0",
                }
            ],
            vehicle_capacity_units="1",
        )

        self.assertIn(
            result["status"],
            ["OPTIMAL", "FEASIBLE"],
        )

        self.assertEqual(
            len(result["allocations"]),
            1,
        )

        self.assertEqual(
            result["allocations"][0]["quantity"],
            "300",
        )

    def test_donor_cannot_supply_more_than_available(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "D1",
                    "medicine_id": "M1",
                    "available_quantity": "100",
                    "capacity_per_unit": "0.00001",
                }
            ],
            recipient_needs=[
                {
                    "recipient_id": "R1",
                    "medicine_id": "M1",
                    "shortage_quantity": "300",
                    "priority": "CRITICAL",
                }
            ],
            routes=[
                {
                    "donor_id": "D1",
                    "recipient_id": "R1",
                    "distance_km": "10",
                }
            ],
            vehicle_capacity_units="1",
        )

        self.assertIn(
            result["status"],
            ["OPTIMAL", "FEASIBLE"],
        )

        allocated = sum(
            float(item["quantity"])
            for item in result["allocations"]
        )

        self.assertLessEqual(
            allocated,
            100,
        )

    def test_recipient_cannot_receive_more_than_shortage(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "D1",
                    "medicine_id": "M1",
                    "available_quantity": "500",
                    "capacity_per_unit": "0.00001",
                }
            ],
            recipient_needs=[
                {
                    "recipient_id": "R1",
                    "medicine_id": "M1",
                    "shortage_quantity": "50",
                    "priority": "HIGH",
                }
            ],
            routes=[
                {
                    "donor_id": "D1",
                    "recipient_id": "R1",
                    "distance_km": "10",
                }
            ],
            vehicle_capacity_units="1",
        )

        self.assertIn(
            result["status"],
            ["OPTIMAL", "FEASIBLE"],
        )

        allocated = sum(
            float(item["quantity"])
            for item in result["allocations"]
        )

        self.assertLessEqual(
            allocated,
            50,
        )

    def test_no_self_transfer(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "F1",
                    "medicine_id": "M1",
                    "available_quantity": "500",
                    "capacity_per_unit": "0.00001",
                }
            ],
            recipient_needs=[
                {
                    "recipient_id": "F1",
                    "medicine_id": "M1",
                    "shortage_quantity": "300",
                    "priority": "CRITICAL",
                }
            ],
            routes=[
                {
                    "donor_id": "F1",
                    "recipient_id": "F1",
                    "distance_km": "0",
                }
            ],
            vehicle_capacity_units="1",
        )

        self.assertEqual(
            result["status"],
            "INFEASIBLE",
        )

        self.assertEqual(
            result["allocations"],
            [],
        )

    def test_transport_capacity_is_respected(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "D1",
                    "medicine_id": "M1",
                    "available_quantity": "1000",
                    "capacity_per_unit": "0.01",
                }
            ],
            recipient_needs=[
                {
                    "recipient_id": "R1",
                    "medicine_id": "M1",
                    "shortage_quantity": "1000",
                    "priority": "HIGH",
                }
            ],
            routes=[
                {
                    "donor_id": "D1",
                    "recipient_id": "R1",
                    "distance_km": "10",
                }
            ],
            vehicle_capacity_units="2",
        )

        self.assertIn(
            result["status"],
            ["OPTIMAL", "FEASIBLE"],
        )

        allocated = sum(
            float(item["quantity"])
            for item in result["allocations"]
        )

        self.assertLessEqual(
            allocated * 0.01,
            2.0,
        )

    def test_multiple_medicines_share_route_capacity(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "D1",
                    "medicine_id": "M1",
                    "available_quantity": "100",
                    "capacity_per_unit": "0.01",
                },
                {
                    "batch_id": "B2",
                    "donor_id": "D1",
                    "medicine_id": "M2",
                    "available_quantity": "100",
                    "capacity_per_unit": "0.01",
                },
            ],
            recipient_needs=[
                {
                    "recipient_id": "R1",
                    "medicine_id": "M1",
                    "shortage_quantity": "100",
                    "priority": "CRITICAL",
                },
                {
                    "recipient_id": "R1",
                    "medicine_id": "M2",
                    "shortage_quantity": "100",
                    "priority": "CRITICAL",
                },
            ],
            routes=[
                {
                    "donor_id": "D1",
                    "recipient_id": "R1",
                    "distance_km": "10",
                }
            ],
            vehicle_capacity_units="1",
        )

        self.assertIn(
            result["status"],
            ["OPTIMAL", "FEASIBLE"],
        )

        total_capacity = sum(
            float(item["capacity_units"])
            for item in result["allocations"]
        )

        self.assertLessEqual(
            total_capacity,
            1.0,
        )

    def test_route_limit_is_respected(self):

        result = optimize_redistribution(
            donor_batches=[
                {
                    "batch_id": "B1",
                    "donor_id": "D1",
                    "medicine_id": "M1",
                    "available_quantity": "100",
                    "capacity_per_unit": "0.00001",
                },
                {
                    "batch_id": "B2",
                    "donor_id": "D2",
                    "medicine_id": "M1",
                    "available_quantity": "100",
                    "capacity_per_unit": "0.00001",
                },
            ],
            recipient_needs=[
                {
                    "recipient_id": "R1",
                    "medicine_id": "M1",
                    "shortage_quantity": "100",
                    "priority": "CRITICAL",
                },
                {
                    "recipient_id": "R2",
                    "medicine_id": "M1",
                    "shortage_quantity": "100",
                    "priority": "HIGH",
                },
            ],
            routes=[
                {
                    "donor_id": "D1",
                    "recipient_id": "R1",
                    "distance_km": "10",
                },
                {
                    "donor_id": "D1",
                    "recipient_id": "R2",
                    "distance_km": "20",
                },
                {
                    "donor_id": "D2",
                    "recipient_id": "R1",
                    "distance_km": "15",
                },
                {
                    "donor_id": "D2",
                    "recipient_id": "R2",
                    "distance_km": "25",
                },
            ],
            vehicle_capacity_units="1",
            max_active_routes=1,
        )

        self.assertIn(
            result["status"],
            ["OPTIMAL", "FEASIBLE"],
        )

        used_routes = {
            (
                item["donor_id"],
                item["recipient_id"],
            )
            for item in result["allocations"]
        }

        self.assertLessEqual(
            len(used_routes),
            1,
        )