from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture

from checkov.common.bridgecrew.bc_source import get_source_type
from checkov.common.bridgecrew.check_type import CheckType
from checkov.kustomize.runner import Runner
from checkov.runner_filter import RunnerFilter
from tests.kustomize.utils import kustomize_exists

RESOURCES_PATH = Path(__file__).parent / "runner/resources"


@pytest.fixture()
def image_cached_result() -> dict[str, Any]:
    return {
        "results": [
            {
                "id": "sha256:f9b91f78b0344fa0efc5583d79e78a90556ab0bb3f93fcbc8728b0b70d29a5db",
                "name": "python:3.9-alpine",
                "distro": "Alpine Linux v3.16",
                "distroRelease": "3.16.1",
                "digest": "sha256:83a343afa488ff14d0c807b62770140d2ec30ef2e83a3a45c4ce62c29623e240",
                "collections": ["All"],
                "packages": [{"type": "os", "name": "zlib", "version": "1.2.12-r1", "licenses": ["Zlib"]}],
                "compliances": [],
                "complianceDistribution": {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0},
                "complianceScanPassed": True,
                "vulnerabilities": [
                    {
                        "id": "CVE-2022-37434",
                        "status": "fixed in 1.2.12-r2",
                        "description": "zlib through 1.2.12 has a heap-based buffer over-read ...",
                        "severity": "low",
                        "packageName": "zlib",
                        "packageVersion": "1.2.12-r1",
                        "link": "https://nvd.nist.gov/vuln/detail/CVE-2022-37434",
                        "riskFactors": ["Has fix", "Recent vulnerability"],
                        "impactedVersions": ["<1.2.12-r2"],
                        "publishedDate": "2022-08-05T07:15:00Z",
                        "discoveredDate": "2022-08-08T13:45:43Z",
                        "fixDate": "2022-08-05T07:15:00Z",
                    }
                ],
                "vulnerabilityDistribution": {"critical": 0, "high": 0, "medium": 0, "low": 1, "total": 1},
                "vulnerabilityScanPassed": True,
            }
        ]
    }


@pytest.fixture()
def license_statuses_result() -> list[dict[str, str]]:
    return [
        {
            "package_name": "openssl",
            "package_version": "1.1.1q-r0",
            "policy": "BC_LIC_1",
            "license": "OpenSSL",
            "status": "OPEN",
        },
        {
            "package_name": "musl",
            "package_version": "1.2.3-r0",
            "policy": "BC_LIC_1",
            "license": "MIT",
            "status": "COMPLIANT",
        },
    ]


@pytest.mark.skipif(os.name == "nt" or not kustomize_exists(), reason="kustomize not installed or Windows OS")
def test_deployment_resources(mocker: MockerFixture, image_cached_result, license_statuses_result):
    from checkov.common.bridgecrew.platform_integration import bc_integration

    # given
    file_name = "image_referencer/overlays/prod/Deployment-default-prod-wordpress.yaml"
    image_name = "wordpress:4.8-apache"
    code_lines = "2-31"
    test_folder = RESOURCES_PATH / "image_referencer/overlays/prod"
    runner_filter = RunnerFilter(run_image_referencer=True)
    bc_integration.bc_source = get_source_type("disabled")

    mocker.patch(
        "checkov.common.images.image_referencer.image_scanner.get_scan_results_from_cache",
        return_value=image_cached_result,
    )
    mocker.patch(
        "checkov.common.images.image_referencer.get_license_statuses",
        return_value=[],
    )

    # when
    runner = Runner()
    runner.templateRendererCommand = "kustomize"
    runner.templateRendererCommandOptions = "build"
    reports = runner.run(root_folder=str(test_folder), runner_filter=runner_filter)

    # then
    assert len(reports) == 2

    kustomize_report = next(report for report in reports if report.check_type == CheckType.KUSTOMIZE)
    sca_image_report = next(report for report in reports if report.check_type == CheckType.SCA_IMAGE)

    assert len(kustomize_report.resources) == 2
    assert len(kustomize_report.passed_checks) == 70
    assert len(kustomize_report.failed_checks) == 20
    assert len(kustomize_report.skipped_checks) == 0
    assert len(kustomize_report.parsing_errors) == 0

    assert len(sca_image_report.resources) == 1
    assert sca_image_report.resources == {
        f"{file_name} ({image_name} lines:{code_lines} (sha256:f9b91f78b0)).zlib",
    }
    assert len(sca_image_report.passed_checks) == 0
    assert len(sca_image_report.failed_checks) == 1
    assert len(sca_image_report.skipped_checks) == 0
    assert len(sca_image_report.parsing_errors) == 0
