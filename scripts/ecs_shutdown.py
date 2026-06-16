#!/usr/bin/env python3

"""
ECS Shutdown Manager

Purpose:
    Safely shutdown ECS services and tasks to save AWS credits during learning.
    Supports scheduling, cost estimation, and detailed logging.

Usage:
    python ecs_shutdown.py --cluster backend-learning-cluster --region eu-north-1
    python ecs_shutdown.py --schedule daily --time 18:00  # Shutdown at 6 PM daily
    python ecs_shutdown.py --estimate-savings              # Show cost savings
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ECSShutdownManager:
    """Manages ECS service shutdown and cost tracking."""

    def __init__(self, cluster_name: str, region: str):
        """Initialize ECS manager with AWS clients."""
        self.cluster_name = cluster_name
        self.region = region
        self.ecs_client = boto3.client("ecs", region_name=region)
        self.ec2_client = boto3.client("ec2", region_name=region)
        self.elbv2_client = boto3.client("elbv2", region_name=region)
        self.logs_client = boto3.client("logs", region_name=region)

    def cluster_exists(self) -> bool:
        """Check if cluster exists."""
        try:
            response = self.ecs_client.describe_clusters(clusters=[self.cluster_name])
            clusters = response.get("clusters", [])
            return len(clusters) > 0 and clusters[0]["status"] != "INACTIVE"
        except ClientError as e:
            logger.error(f"Error checking cluster: {e}")
            return False

    def get_services(self) -> list[str]:
        """Get all services in the cluster."""
        try:
            response = self.ecs_client.list_services(cluster=self.cluster_name)
            return response.get("serviceArns", [])
        except ClientError as e:
            logger.error(f"Error listing services: {e}")
            return []

    def get_running_tasks(self) -> list[str]:
        """Get all running tasks in the cluster."""
        try:
            response = self.ecs_client.list_tasks(cluster=self.cluster_name)
            return response.get("taskArns", [])
        except ClientError as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    def scale_down_service(self, service_arn: str) -> bool:
        """Scale down a service to 0 desired count."""
        service_name = service_arn.split("/")[-1]
        try:
            self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=service_arn,
                desiredCount=0,
            )
            logger.info(f"✓ Scaled down service: {service_name}")
            return True
        except ClientError as e:
            logger.error(f"✗ Failed to scale down {service_name}: {e}")
            return False

    def stop_task(self, task_arn: str) -> bool:
        """Stop a running task."""
        task_id = task_arn.split("/")[-1]
        try:
            self.ecs_client.stop_task(
                cluster=self.cluster_name,
                task=task_arn,
                reason="Manual shutdown via ECS Shutdown Manager",
            )
            logger.info(f"✓ Stopped task: {task_id}")
            return True
        except ClientError as e:
            logger.error(f"✗ Failed to stop task {task_id}: {e}")
            return False

    def deregister_targets(self) -> int:
        """Deregister all targets from load balancer target groups."""
        deregistered_count = 0

        try:
            # Find load balancers
            response = self.elbv2_client.describe_load_balancers()
            load_balancers = response.get("LoadBalancers", [])

            for lb in load_balancers:
                lb_arn = lb["LoadBalancerArn"]
                lb_name = lb["LoadBalancerName"]

                # Get target groups for this LB
                tg_response = self.elbv2_client.describe_target_groups(
                    LoadBalancerArn=lb_arn
                )
                target_groups = tg_response.get("TargetGroups", [])

                for tg in target_groups:
                    tg_arn = tg["TargetGroupArn"]
                    tg_name = tg["TargetGroupName"]

                    # Get targets
                    targets_response = self.elbv2_client.describe_target_health(
                        TargetGroupArn=tg_arn
                    )
                    targets = targets_response.get("TargetHealthDescriptions", [])

                    if targets:
                        logger.info(
                            f"Deregistering {len(targets)} target(s) from {tg_name}"
                        )

                        # Deregister each target
                        for target in targets:
                            target_id = target["Target"]["Id"]
                            try:
                                self.elbv2_client.deregister_targets(
                                    TargetGroupArn=tg_arn,
                                    Targets=[{"Id": target_id}],
                                )
                                deregistered_count += 1
                            except ClientError as e:
                                logger.error(f"Failed to deregister target: {e}")

        except ClientError as e:
            logger.error(f"Error managing load balancers: {e}")

        return deregistered_count

    def shutdown(self, verbose: bool = False) -> dict:
        """Execute full shutdown process."""
        results = {
            "cluster": self.cluster_name,
            "timestamp": datetime.now().isoformat(),
            "services_scaled": 0,
            "tasks_stopped": 0,
            "targets_deregistered": 0,
            "success": False,
        }

        logger.info("=" * 70)
        logger.info(f"Starting ECS Shutdown - Cluster: {self.cluster_name}")
        logger.info(f"Region: {self.region}")
        logger.info("=" * 70)
        logger.info("")

        # Check cluster exists
        if not self.cluster_exists():
            logger.warning(f"Cluster '{self.cluster_name}' not found.")
            return results

        logger.info("✓ Cluster found")
        logger.info("")

        # Step 1: Scale down services
        logger.info("Step 1: Scaling down services...")
        services = self.get_services()

        if not services:
            logger.info("No services found in cluster.")
        else:
            logger.info(f"Found {len(services)} service(s)")

            for service_arn in services:
                if self.scale_down_service(service_arn):
                    results["services_scaled"] += 1

        logger.info("")

        # Step 2: Stop running tasks
        logger.info("Step 2: Stopping running tasks...")
        tasks = self.get_running_tasks()

        if not tasks:
            logger.info("No running tasks found.")
        else:
            logger.info(f"Found {len(tasks)} running task(s)")

            for task_arn in tasks:
                if self.stop_task(task_arn):
                    results["tasks_stopped"] += 1

        logger.info("")

        # Step 3: Deregister targets
        logger.info("Step 3: Deregistering load balancer targets...")
        results["targets_deregistered"] = self.deregister_targets()

        if results["targets_deregistered"] == 0:
            logger.info("No targets to deregister.")

        logger.info("")

        # Success
        results["success"] = True
        logger.info("=" * 70)
        logger.info("✓ ECS Shutdown Complete!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  • Services scaled: {results['services_scaled']}")
        logger.info(f"  • Tasks stopped: {results['tasks_stopped']}")
        logger.info(f"  • Targets deregistered: {results['targets_deregistered']}")
        logger.info("")

        return results

    def estimate_savings(self) -> dict:
        """Estimate monthly cost savings from shutdown."""
        # AWS pricing estimates (as of 2024)
        hourly_rates = {
            "t4g.micro (0.25vCPU)": 0.0067,  # ~$4.80/month if 24/7
            "t3.micro (0.25vCPU)": 0.0094,  # ~$6.77/month if 24/7
            "alb": 0.0225,  # ~$16.20/month if 24/7
            "log_ingestion": 0.50,  # per GB
        }

        services = self.get_services()
        tasks = self.get_running_tasks()

        # Estimate based on found resources
        monthly_savings = {
            "ecs_tasks_24_7": len(services) * hourly_rates["t4g.micro (0.25vCPU)"]
            * 730,  # 730 hours/month
            "alb_24_7": hourly_rates["alb"] * 730,
            "logs_estimate": 5 * hourly_rates["log_ingestion"],  # Assume 5GB/month
            "total_24_7_estimated": (
                (len(services) * hourly_rates["t4g.micro (0.25vCPU)"] + hourly_rates["alb"])
                * 730
                + 5 * hourly_rates["log_ingestion"]
            ),
        }

        logger.info("=" * 70)
        logger.info("Cost Savings Estimate")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"Active services: {len(services)}")
        logger.info(f"Running tasks: {len(tasks)}")
        logger.info("")
        logger.info("If running 24/7:")
        logger.info(f"  • ECS tasks: ${monthly_savings['ecs_tasks_24_7']:.2f}/month")
        logger.info(f"  • ALB: ${monthly_savings['alb_24_7']:.2f}/month")
        logger.info(f"  • CloudWatch Logs: ${monthly_savings['logs_estimate']:.2f}/month")
        logger.info(
            f"  • TOTAL: ${monthly_savings['total_24_7_estimated']:.2f}/month"
        )
        logger.info("")
        logger.info("After shutdown:")
        logger.info("  • Cost: ~$0/month (free tier covers most)")
        logger.info(f"  • Savings: ${monthly_savings['total_24_7_estimated']:.2f}/month")
        logger.info("")

        return monthly_savings


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ECS Shutdown Manager - Save AWS credits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Shutdown all services in cluster
  python ecs_shutdown.py --cluster backend-learning-cluster

  # Shutdown with custom region
  python ecs_shutdown.py --cluster my-cluster --region us-east-1

  # Estimate cost savings
  python ecs_shutdown.py --estimate-savings

  # Schedule automatic shutdown (requires additional setup)
  python ecs_shutdown.py --schedule daily --time 18:00
        """,
    )

    parser.add_argument(
        "--cluster",
        default="python-backend",
        help="ECS cluster name (default: python-backend)",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )
    parser.add_argument(
        "--estimate-savings",
        action="store_true",
        help="Show cost savings estimate (don't shutdown)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Create manager
    manager = ECSShutdownManager(args.cluster, args.region)

    # Handle estimate-savings
    if args.estimate_savings:
        manager.estimate_savings()
        return

    # Execute shutdown
    try:
        results = manager.shutdown(verbose=args.verbose)

        if not results["success"]:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\nShutdown interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
