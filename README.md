# k8s-user-provisioner
Creation de playground individuel sous le cluster k8s de Zerofiltre 

## Créez votre environnement

```shell
curl --location 'https://provisioner.zerofiltre.tech/provisioner' \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json' \
--data-raw '{
    "full_name":"votre_nom_et",
    "email":"ou_votre_adresse_email"
}'
```

## Exécuter le projet

### Installer l'en virtuel

```
python -m venv .venv 
```
Le dossier .venv sera créé à la racine du projet

### Activer l'environnement virtuel 

Se placer à la racine du projet et faire:
* Sous windows
```
.venv\Scripts\activate
```

* Sous linux 
```
source .venv/bin/activate
```

### Démarrer l'application en local

Créer un fichier .env à la racine du projet et y mettre le contenu [situé ici](https://vault.zerofiltre.tech/ui/vault/secrets/dev/show/zerofiltre-approvisionner)  

Pensez à remplacer les valeurs xxx par celles situées dans le même répertoire vault.

Puis faire: `python run.py`