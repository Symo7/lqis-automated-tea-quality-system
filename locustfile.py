import json
import uuid
import uuid
from locust import HttpUser, task, between

class InspectorAPIUser(HttpUser):
    """
    Simulates a heavy-duty field Inspector sending packets of image + JSON
    data straight to the sync_submit endpoint.
    """
    wait_time = between(1, 5) # wait between 1 to 5 seconds between tasks
    
    # Needs to match a user in the local seeded database (from setup_roles / seed_demo_data)
    # We will grab a session cookie by logging in on_start.
    username = "inspector1"
    password = "admin123"

    def on_start(self):
        # We must log in to get a valid Django session/CSRF token since the endpoint requires auth.
        # Ensure your local server is running with `python manage.py runserver`
        self.client.post("/login/", {
            "username": self.username,
            "password": self.password
        })

    def _generate_valid_payload(self) -> dict:
        """
        Creates a JSON body mimicking an offline capture packet representing 
        a PERFECTLY valid ForeignKey hierarchy (assuming the seed data F001 -> BC101 -> SUP001 -> Batch exists).
        """
        # We will use the IDs from the seed_demo_data.py execution
        # Factory: 1 (Kericho Main)
        # Center: 1 (BC101)
        # Supplier: 1 (Green Valley Farmers)
        # Batch: 1 (BATCH-2026-001)
        sub_id = uuid.uuid4().hex
        return {
            "local_id": sub_id,
            "factory": 1,
            "tea_buying_center": 1,
            "supplier": 1,
            "batch": 1,
            "intake_timestamp": "2026-03-20T12:00:00",
            "moisture_pct": 7.5,
            "foreign_matter_pct": 1.2,
            "notes": "Locust stress test submission",
            # Standard invisible 1x1 png file encoded to base64 for test padding
            "image_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        }

    @task(3)
    def submit_valid_sample(self):
        """
        Sends perfectly valid payloads to bombard the system to test @transaction.atomic 
        and parallel INSERT locking.
        """
        payload = self._generate_valid_payload()
        with self.client.post("/sampling/sync-submit/", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.success() # Rate limit hit is expected in rapid fire
            else:
                response.failure(f"Valid payload failed with {response.status_code}: {response.text}")

    @task(1)
    def submit_duplicate_sample(self):
        """
        Tests the `existing = FactoryIntakeSample.objects.filter(client_submission_id=client_id)` 
        block. Should return 200 {"status": "duplicate"}.
        """
        payload = self._generate_valid_payload()
        
        # Initial submission
        self.client.post("/sampling/sync-submit/", json=payload)
        
        # Parallel duplicate spam
        with self.client.post("/sampling/sync-submit/", json=payload, catch_response=True) as response:
            if response.status_code == 200 and "duplicate" in response.text:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Duplicate protection failed: {response.status_code} {response.text}")

    @task(1)
    def submit_malformed_json_spam(self):
        """
        Throws completely broken strings instead of JSON. The backend should trap this 
        with json.JSONDecodeError and yield 400 Bad Request safely without tracebacks.
        """
        with self.client.post("/sampling/sync-submit/", data="THIS { IS ] NOT [ JSON", catch_response=True) as response:
            if response.status_code == 400:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"System crashed on malformed JSON: {response.status_code}")

    @task(1)
    def submit_mismatched_hierarchy(self):
        """
        Attempts to submit a sample where the Batch does not belong to the selected Factory. 
        Tests the rigid ForeignKey security validations recently implemented.
        """
        payload = self._generate_valid_payload()
        # F2 (Nandi) vs BC101 (Kericho). This is a hierarchy mismatch!
        payload["factory"] = 2 
        
        with self.client.post("/sampling/sync-submit/", json=payload, catch_response=True) as response:
            if response.status_code == 400 and "does not belong" in response.text:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Hierarchy security failed! {response.status_code}")
