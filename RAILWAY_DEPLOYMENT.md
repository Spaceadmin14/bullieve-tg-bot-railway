# Déploiement Railway

## Variables d'environnement à configurer

```env
TELEGRAM_BOT_TOKEN=8083638248:AAF5A1Re49xWBrJn5kNr2jhQtIRRdNRWQqM
TELEGRAM_CHAT_ID=-1002421701303
SOLANA_RPC_URL=https://rpc.helius.xyz/?api-key=2258d67f-c201-443b-abbe-571505a4d516
SOLANA_ALT_RPC_URL=https://api.mainnet-beta.solana.com
PRIMARY_WALLET_ADDRESS=6674vbB9LRJKymhEz9DxxJc5HyXbCsSVFh1jGuL7xM6B
SECONDARY_WALLET_ADDRESS=5aYBTU9x6F8qmytdmAiLcRQyPEVjBiGN2tHArFbop8V5
BULLIEVE_MINT_ADDRESS=HdzMjvQvFP9nxp1X2NbHFptZK1G6ASsyRcxNdn65ABxi
BURN_INCINERATOR_ADDRESS=11111111111111111111111111111112
POLL_INTERVAL_SECONDS=5
STATE_FILE_PATH=/app/data/state.json
MANUAL_PRICE_FILE_PATH=/app/data/manual_prices.json
```

## Étapes de déploiement

1. **Créer un compte** sur [railway.app](https://railway.app)
2. **Connecter GitHub** à ton compte Railway
3. **"New Project"** → "Deploy from GitHub repo"
4. **Sélectionner ce repo** ou créer un nouveau
5. **Ajouter les variables d'environnement** ci-dessus dans Railway Dashboard
6. **Déployer** - Railway va automatiquement construire et lancer le bot

## Monitoring

- **Logs** : Dashboard Railway → Ton projet → Logs
- **Redémarrage** : Dashboard → "Redeploy" button
- **Variables** : Dashboard → Variables (modifier et sauvegarder)

## Avantages Railway

✅ **500h/mois gratuites** (20 jours)  
✅ **Restart automatique** si crash  
✅ **Déploiement simple** via GitHub  
✅ **Variables d'environnement** sécurisées  
✅ **Bot 24/7** pendant les heures gratuites
