# Tableau de bord électoral — guide « en 1 jour »

Tout le code est prêt. Le travail consiste à : créer les comptes → copier les fichiers → remplir les `.env` → lancer les commandes.
**Travaillez à 4 en parallèle** (voir la répartition en bas).

Règle d'or : **valider chaque étape avant de passer à la suivante** (la ligne « ✅ Test » de chaque bloc).

---

## H0 → H1 : comptes et machines (tout le monde en même temps)

| Qui | Action |
|---|---|
| P1 | **Azure** : VM Ubuntu 22.04, taille **B2s**, accès SSH par clé. Ne rien ouvrir d'autre que le port 22. |
| P2 | **Oracle** : VM Ubuntu 22.04 **VM.Standard.A1.Flex** (2 OCPU, 12 Go). Si « out of capacity » : essayer un autre Availability Domain, ou 1 OCPU / 6 Go. |
| P3 | **Google Cloud** : VM **e2-medium** Ubuntu 22.04. |
| P4 | Comptes **Tailscale**, **Render**, **Vercel**, **Cloudflare**, **GitHub** (créer un dépôt privé et y pousser ce dossier). Bot **Telegram** (voir H4). |

Sur **chacune des 3 VM** :
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                       # ouvrir le lien affiché, se connecter au MÊME compte Tailscale
tailscale ip -4                         # NOTER cette IP (100.x.x.x)
git clone <votre dépôt> && cd projet-elections
```
**Oracle uniquement** (son pare-feu interne bloque tout sauf SSH) :
```bash
sudo iptables -I INPUT -i tailscale0 -j ACCEPT && sudo netfilter-persistent save
```
✅ Test : depuis Azure, `ping <IP Oracle>` et `ping <IP GCP>` répondent.

Notez les 3 IP Tailscale dans un message partagé du groupe : `AZURE_IP`, `ORACLE_IP`, `GCP_IP`.

---

## H1 → H2 : Google Cloud (etcd d'abord, car Patroni en a besoin)

```bash
cd gcp
cp .env.example .env && nano .env        # mettre les 3 IP
sudo apt install -y gettext-base && ./setup.sh
docker compose up -d etcd controller prometheus alertmanager grafana
```
✅ Test : `curl localhost:5000/active` → `{"cloud":"azure", ...}`
(MirrorMaker est lancé plus tard, quand les deux Kafka existent.)

---

## H2 → H3 : Azure (le cloud primaire)

```bash
cd cloud-node
cp .env.example .env && nano .env        # CLOUD=azure, MY_IP=<IP Azure>, les 3 IP, mots de passe…
docker compose up -d --build
docker compose logs -f postgres          # attendre « i am the leader with the lock »
```
✅ Tests :
```bash
docker compose ps                                                   # tout est "running"
psql -h 127.0.0.1 -U postgres -c "select count(*) from bureaux"     # 48  (sudo apt install postgresql-client)
curl -X POST localhost:8000/votes -H "x-internal-key: <INTERNAL_KEY>" -H "Content-Type: application/json" \
  -d '{"bureau_id":"B101","votes":{"Liste A":100,"Liste B":80,"Liste C":50},"timestamp":"2026-11-24T18:00:00+00:00"}'
curl localhost:8000/results                                         # B101 apparaît
docker compose logs aggregator                                      # "agrege B101"
```

---

## H3 → H4 : Oracle (copie exacte d'Azure)

Même dossier `cloud-node`, même `.env`, en changeant **seulement** `CLOUD=oracle` et `MY_IP=<IP Oracle>`.
```bash
docker compose up -d --build
docker compose logs -f postgres          # doit dire « replica » / « following leader azure »
```
Puis **sur GCP** : `docker compose up -d mirrormaker`

✅ Tests :
- `docker compose exec postgres /opt/patroni/bin/patronictl -c /etc/patroni/patroni.yml list` → azure = Leader, oracle = Replica, Lag ≈ 0
- Logs de l'agrégateur Oracle : « en attente » (normal, il est en secours)
- Sur Oracle : `docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list` → `azure.votes` apparaît (MirrorMaker fonctionne)
- Prometheus : ouvrir `http://<GCP_IP>:9090/targets` depuis un PC **qui a Tailscale installé** → toutes les cibles « UP »

---

## H4 → H5 : Telegram + Cloudflare Worker

1. Dans Telegram, parler à **@BotFather** → `/newbot` → noter le **BOT_TOKEN**.
2. Créer un groupe, y ajouter le bot, écrire un message, puis ouvrir
   `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` → noter le `chat.id` (nombre négatif) = **CHAT_ID**.
3. Déployer le Worker (sur un PC avec Node.js) :
```bash
cd worker
npx wrangler login
npx wrangler deploy                     # note l'URL https://elections-alertes.xxx.workers.dev
npx wrangler secret put BOT_TOKEN
npx wrangler secret put CHAT_ID
npx wrangler secret put SECRET          # même valeur que WORKER_SECRET dans les .env
```
4. Mettre `WORKER_URL` et `WORKER_SECRET` dans le `.env` d'Azure **et** d'Oracle, puis `docker compose up -d relay`.

✅ Test : `curl -X POST <WORKER_URL> -H "x-secret: <SECRET>" -H "Content-Type: application/json" -d '{"type":"TEST","bureau_id":"B101","details":"essai","created_at":"maintenant"}'` → message reçu dans le groupe.

---

## H5 → H6 : Render (2 services, même dossier)

1. Console Tailscale → **Settings → Keys → Generate auth key** : cocher **Reusable** et **Ephemeral**.
2. Render → **New → Web Service** → votre dépôt GitHub → **Root Directory : `render`**, Runtime **Docker**, plan Free.
   Variables d'environnement :

| Variable | Service ingestion | Service dashboard |
|---|---|---|
| `APP_MODULE` | `ingestion` | `dashboard` |
| `TS_HOSTNAME` | `render-ingestion` | `render-dashboard` |
| `TS_AUTHKEY` | la clé Tailscale | la même |
| `CONTROLLER_URL` | `http://<GCP_IP>:5000` | idem |
| `INTERNAL_KEY` | même valeur que les `.env` | (inutile) |

3. Créer le 2ᵉ service de la même manière.

✅ Test : `https://<ingestion>.onrender.com/docs` s'ouvre. La machine `render-ingestion` apparaît dans la console Tailscale.

---

## H6 → H7 : Vercel

1. Mettre les 2 URL Render dans `vercel/config.js`, puis faire un commit et un push.
2. Vercel → **Add New Project** → le dépôt → **Root Directory : `vercel`**, Framework **Other** → Deploy.

✅ Test complet de bout en bout :
```bash
python3 simulator.py https://<ingestion>.onrender.com --fraudes
```
→ le tableau de bord se remplit, 4 alertes arrivent sur Telegram, et les envois décimal, négatif et faux token sont refusés (422 / 401).

Pour une démo propre, vider les données avant :
`psql -h 127.0.0.1 -U postgres -c "truncate votes, anomalies"`

---

## H7 → H8 : Grafana + test de bascule

**Grafana** : `http://<GCP_IP>:3000` (admin / admin123) → Dashboards → Import → ID **1860** (Node Exporter Full) → source Prometheus.
Ajouter un panneau avec `kafka_up`, `pg_local_leader`, `failover_oracle_actif`, `rate(votes_agreges_total[1m])`.

**Bascule** (le moment fort de la démo) :
```bash
# terminal 1 (PC) : flux continu
python3 simulator.py https://<ingestion>.onrender.com --boucle
# terminal 2 : sur AZURE
docker compose stop          # ou arrêter la VM depuis le portail Azure
```
Ce qu'on doit voir en 30 à 45 s :
- Prometheus : alerte `AzureDown` ;
- `docker compose logs controller` sur GCP : `*** BASCULE azure -> oracle` ;
- Patroni : Oracle devient Leader, et l'agrégateur Oracle passe « ACTIF » ;
- tableau de bord : badge **ORACLE** ; les totaux continuent de monter et ne baissent jamais.

Retour : sur Azure `docker compose start` → Azure redevient réplique (pg_rewind), l'alerte se résout et le controller revient sur Azure. Les votes reçus par Azure sont copiés par MirrorMaker vers Oracle, qui reste leader PostgreSQL. **Aucune perte.**

---

## Répartition à 4

| Personne | Partie | Créneau |
|---|---|---|
| P1 | VM Azure + nœud cloud | H0–H3 puis aide sur la bascule |
| P2 | VM Oracle + Patroni + MirrorMaker | H0–H4 |
| P3 | VM GCP + Prometheus/Grafana/controller + test de bascule | H0–H2, H7–H8 |
| P4 | Comptes, Telegram, Worker, Render, Vercel, slides/rapport | H0–H7 |

Garder **2 heures** en fin de journée pour les imprévus et une répétition de la démo.

## Choix techniques à justifier dans le rapport
- **UPSERT idempotent** : rejouer un vote après une bascule ne change pas les totaux (zéro doublon, zéro perte).
- **Oracle inactif** : ses services ne traitent que si son PostgreSQL est leader Patroni.
- **Render ↔ clouds en HTTP via Tailscale userspace** : Render n'autorise pas de VPN réseau, et Kafka ne passe pas par un proxy HTTP. C'est donc `cloud_api` qui produit dans Kafka.
- **Relay → Worker** : un Worker Cloudflare ne peut ni rejoindre Tailscale ni parler le protocole Kafka.
- **Limites** : un seul etcd (point unique de défaillance), un broker Kafka par cloud, offres gratuites (Render se met en veille après 15 min).

## Dépannage rapide
| Symptôme | Cause probable |
|---|---|
| Oracle injoignable via Tailscale | règle `iptables` oubliée (H0) |
| Patroni « waiting for leader » | etcd sur GCP non lancé, ou `GCP_IP` faux |
| Kafka : clients bloqués | `MY_IP` faux dans le `.env` (adresse annoncée par Kafka) |
| Render 503 | service endormi (ouvrir l'URL pour le réveiller), ou `TS_AUTHKEY` expirée |
| Pas de message Telegram | `WORKER_URL` / `SECRET` différents entre le `.env` et Cloudflare |
| Le build ARM échoue sur Oracle | relancer `docker compose build --no-cache` (toutes les images utilisées existent en arm64) |
