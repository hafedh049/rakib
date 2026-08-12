#!/usr/bin/env sh
# Build and deploy Rakib onto the k3s cluster. Run ON the VPS:
#     sh /root/rakib/src/deploy/deploy.sh [--skip-build]
#
# Everything lives in the `reclamations` namespace. The only thing borrowed from
# elsewhere on the cluster is the SMTP relay credential.
set -eu

SRC="${SRC:-/root/rakib/src}"
NS=reclamations
TAG="${TAG:-latest}"

log() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# ---------------------------------------------------------------- namespace --
log "namespace"
kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS"

# ------------------------------------------------------------------ secrets --
# Generated once and left alone: rotating JWT_SECRET on every deploy would log
# every user out, and rotating TRACKING_TOKEN_SECRET would break every tracking
# link a claimant has already been given.
log "secrets"
if ! kubectl -n "$NS" get secret rakib-secret >/dev/null 2>&1; then
  kubectl -n "$NS" create secret generic rakib-secret \
    --from-literal=JWT_SECRET="$(openssl rand -hex 32)" \
    --from-literal=TRACKING_TOKEN_SECRET="$(openssl rand -hex 32)" \
    --from-literal=S3_ACCESS_KEY=rakib \
    --from-literal=S3_SECRET_KEY="$(openssl rand -hex 20)"
  echo "created rakib-secret"
else
  echo "rakib-secret already present — left untouched"
fi

# SMTP: copied blind from the authorised source secret. Values are never printed.
log "smtp credentials"
SMTP_HOST=$(kubectl -n elitetek-academy get secret eta-mail-secret \
  -o jsonpath='{.data.RELAYHOST}' | base64 -d | sed 's/^\[//; s/\].*$//')
SMTP_USER=$(kubectl -n elitetek-academy get secret eta-mail-secret \
  -o jsonpath='{.data.RELAYHOST_USERNAME}' | base64 -d)
SMTP_PASS=$(kubectl -n elitetek-academy get secret eta-mail-secret \
  -o jsonpath='{.data.RELAYHOST_PASSWORD}' | base64 -d)

kubectl -n "$NS" patch secret rakib-secret --type merge -p "$(cat <<JSON
{"stringData":{"SMTP_HOST":"${SMTP_HOST}","SMTP_USERNAME":"${SMTP_USER}","SMTP_PASSWORD":"${SMTP_PASS}","SMTP_FROM":"${SMTP_USER}"}}
JSON
)" >/dev/null
echo "smtp relay wired (host: ${SMTP_HOST})"

# ------------------------------------------------------------------- images --
if [ "${1:-}" != "--skip-build" ]; then
  log "building backend image"
  docker build -q -t "rakib-backend:${TAG}" "$SRC/backend"

  log "building frontend image"
  docker build -q -t "rakib-frontend:${TAG}" "$SRC/frontend"

  log "importing into k3s containerd"
  docker save "rakib-backend:${TAG}" | k3s ctr images import -
  docker save "rakib-frontend:${TAG}" | k3s ctr images import -
fi

# ------------------------------------------------------------------- apply ---
log "applying manifests"
kubectl apply -f "$SRC/deploy/k8s/rakib.yaml"

log "rolling out"
kubectl -n "$NS" rollout restart deploy/api deploy/worker deploy/notifier deploy/web \
  >/dev/null 2>&1 || true

for deployment in mongo redis minio api worker notifier web; do
  kubectl -n "$NS" rollout status "deploy/$deployment" --timeout=180s
done

log "readiness"
kubectl -n "$NS" exec deploy/api -- \
  python -c "import urllib.request,json;print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/ready')),indent=2))"

log "done"
kubectl -n "$NS" get pods
