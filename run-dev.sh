#!/usr/bin/env bash
set -x

set -euo pipefail

export DJANGO_DEBUG=true

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE="${PROJECT_ROOT}/apptainer/slurm-manager-ldap.sif"
SOURCE="${PROJECT_ROOT}/app"

if [[ ! -f "$IMAGE" ]]; then
    echo "ERROR: Container not found:"
    echo "  $IMAGE"
    exit 1
fi

echo "Starting Django development server..."
echo "Source:    $SOURCE"
echo "Container: $IMAGE"
echo
echo "Django will listen on:"
echo "  http://0.0.0.0:8000/"
echo

singularity exec --bind "${SOURCE}:/workspace" \
    --bind /etc/nsswitch.conf:/etc/nsswitch.conf:ro \
    --bind /run/nslcd:/run/nslcd:ro \
    --bind /usr/lib64/libmunge.so.2:/usr/lib64/libmunge.so.2:ro \
    --bind /etc/passwd:/etc/passwd:ro \
    --bind /etc/group:/etc/group:ro \
    --bind /cm/shared/apps:/cm/shared/apps:ro \
    --bind /run/munge:/run/munge \
    "${IMAGE}" \
    python /workspace/manage.py runserver 0.0.0.0:8000
