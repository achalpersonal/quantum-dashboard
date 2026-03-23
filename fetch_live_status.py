#!/usr/bin/env python3
"""
Live QPU Status Fetcher

Fetches real-time availability from:
- AWS Braket (IonQ, Rigetti, QuEra, IQM, AQT)
- IBM Quantum (Heron, Eagle, etc.)
- IonQ Status API (public, no auth needed)

Setup:
1. AWS Braket: Configure AWS CLI with `aws configure` or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
2. IBM Quantum: Set IBM_QUANTUM_TOKEN environment variable (get from https://quantum.ibm.com)

Usage:
    python3 fetch_live_status.py

Output: Updates data/live_status.json which the HTML dashboard reads
"""

import json
import os
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "live_status.json"

def fetch_ionq_public_status():
    """Fetch IonQ status from their public Statuspage.io API (no auth needed)"""
    print("Fetching IonQ public status...")

    try:
        url = "https://status.ionq.co/api/v2/summary.json"
        req = urllib.request.Request(url, headers={"User-Agent": "QPU-Dashboard/1.0"})

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        components = {}
        for comp in data.get("components", []):
            components[comp["name"]] = {
                "status": comp["status"],
                "updated_at": comp["updated_at"]
            }

        incidents = []
        for incident in data.get("incidents", []):
            if incident.get("status") != "resolved":
                incidents.append({
                    "name": incident["name"],
                    "status": incident["status"],
                    "impact": incident.get("impact"),
                    "started_at": incident.get("started_at")
                })

        return {
            "provider": "IonQ (Public)",
            "source": "status.ionq.co",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "overall_status": data.get("status", {}).get("indicator", "unknown"),
            "components": components,
            "active_incidents": incidents
        }

    except Exception as e:
        print(f"  Error: {e}")
        return {"provider": "IonQ (Public)", "error": str(e)}


def fetch_aws_braket_status():
    """Fetch device status from AWS Braket (requires AWS credentials)"""
    print("Fetching AWS Braket status...")

    try:
        import boto3
    except ImportError:
        print("  boto3 not installed. Run: pip3 install boto3")
        return {"provider": "AWS Braket", "error": "boto3 not installed"}

    try:
        # Check if credentials are available
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            return {"provider": "AWS Braket", "error": "No AWS credentials configured"}

        devices = []
        regions = ["us-east-1", "us-west-1", "eu-north-1"]

        for region in regions:
            try:
                braket = boto3.client("braket", region_name=region)
                response = braket.search_devices(
                    filters=[{"name": "deviceType", "values": ["QPU"]}]
                )

                for device in response.get("devices", []):
                    # Get detailed device info
                    device_arn = device["deviceArn"]
                    try:
                        detail = braket.get_device(deviceArn=device_arn)
                        devices.append({
                            "name": detail["deviceName"],
                            "provider": detail["providerName"],
                            "arn": device_arn,
                            "status": detail["deviceStatus"],  # ONLINE, OFFLINE, RETIRED
                            "region": region,
                            "type": detail["deviceType"],
                            "queue_depth": detail.get("deviceQueueInfo", [])
                        })
                    except Exception as e:
                        print(f"    Error getting {device_arn}: {e}")

            except Exception as e:
                print(f"  Error in {region}: {e}")

        return {
            "provider": "AWS Braket",
            "source": "boto3 API",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "devices": devices
        }

    except Exception as e:
        print(f"  Error: {e}")
        return {"provider": "AWS Braket", "error": str(e)}


def fetch_ibm_quantum_status():
    """Fetch backend status from IBM Quantum (requires API token)"""
    print("Fetching IBM Quantum status...")

    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if not token:
        print("  IBM_QUANTUM_TOKEN not set")
        return {"provider": "IBM Quantum", "error": "IBM_QUANTUM_TOKEN environment variable not set"}

    try:
        # First, get IAM token
        iam_url = "https://iam.cloud.ibm.com/identity/token"
        iam_data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={token}"

        req = urllib.request.Request(
            iam_url,
            data=iam_data.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            iam_response = json.loads(response.read().decode())
            bearer_token = iam_response["access_token"]

        # Fetch backends
        backends_url = "https://api.quantum-computing.ibm.com/runtime/backends"
        req = urllib.request.Request(
            backends_url,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            backends = json.loads(response.read().decode())

        devices = []
        for backend in backends.get("devices", backends) if isinstance(backends, dict) else backends:
            if isinstance(backend, dict):
                devices.append({
                    "name": backend.get("backend_name", backend.get("name", "unknown")),
                    "status": "operational" if backend.get("operational", backend.get("status") == "active") else "offline",
                    "pending_jobs": backend.get("pending_jobs", 0),
                    "qubits": backend.get("n_qubits", backend.get("num_qubits")),
                    "status_msg": backend.get("status_msg", "")
                })

        return {
            "provider": "IBM Quantum",
            "source": "IBM Quantum API",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "devices": devices
        }

    except urllib.error.HTTPError as e:
        print(f"  HTTP Error: {e.code} - {e.reason}")
        return {"provider": "IBM Quantum", "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        print(f"  Error: {e}")
        return {"provider": "IBM Quantum", "error": str(e)}


def fetch_qiskit_ibm_status():
    """Alternative: Use qiskit-ibm-runtime if installed"""
    print("Trying qiskit-ibm-runtime...")

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService

        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if not token:
            return None

        service = QiskitRuntimeService(channel="ibm_quantum", token=token)
        backends = service.backends()

        devices = []
        for backend in backends:
            status = backend.status()
            config = backend.configuration()
            devices.append({
                "name": backend.name,
                "status": "operational" if status.operational else "offline",
                "pending_jobs": status.pending_jobs,
                "qubits": config.n_qubits if hasattr(config, 'n_qubits') else None,
                "status_msg": status.status_msg
            })

        return {
            "provider": "IBM Quantum",
            "source": "qiskit-ibm-runtime",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "devices": devices
        }

    except ImportError:
        return None
    except Exception as e:
        print(f"  qiskit error: {e}")
        return None


def main():
    print("=" * 60)
    print("QPU Live Status Fetcher")
    print("=" * 60)
    print()

    results = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "sources": {}
    }

    # Always fetch IonQ (public, no auth)
    results["sources"]["ionq"] = fetch_ionq_public_status()

    # Try AWS Braket
    results["sources"]["aws_braket"] = fetch_aws_braket_status()

    # Try IBM Quantum (qiskit first, then REST API)
    ibm_result = fetch_qiskit_ibm_status()
    if ibm_result is None:
        ibm_result = fetch_ibm_quantum_status()
    results["sources"]["ibm_quantum"] = ibm_result

    # Save results
    DATA_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 60)
    print(f"Results saved to: {OUTPUT_FILE}")
    print("=" * 60)

    # Print summary
    print("\nSummary:")
    for source, data in results["sources"].items():
        if "error" in data:
            print(f"  {source}: ❌ {data['error']}")
        elif "devices" in data:
            online = sum(1 for d in data["devices"] if d.get("status") in ["ONLINE", "operational"])
            print(f"  {source}: ✅ {len(data['devices'])} devices ({online} online)")
        elif "components" in data:
            operational = sum(1 for c in data["components"].values() if c.get("status") == "operational")
            print(f"  {source}: ✅ {len(data['components'])} components ({operational} operational)")

    print("\nTo enable more sources:")
    print("  AWS Braket: aws configure")
    print("  IBM Quantum: export IBM_QUANTUM_TOKEN='your-token-from-quantum.ibm.com'")


if __name__ == "__main__":
    main()
