# Intégration Groupe 3F pour Home Assistant

<p align="center">
  <img src="icon.png" alt="Logo Groupe 3F" width="150">
</p>

Cette intégration permet de récupérer votre consommation d'eau (Chaude et Froide) directement depuis votre espace client [Groupe 3F](https://eclient.groupe3f.fr/).

## Fonctionnalités

*   **Suivi de consommation** : Récupération des index d'eau chaude et froide.
*   **Historique complet** : Importation automatique de l'historique de consommation (jusqu'à 2 ans) dans Home Assistant.
*   **Dashboard Énergie** : Compatibilité native avec le tableau de bord Énergie.
*   **Authentification sécurisée** : Support complet de l'authentification à deux facteurs (Code par Email).

## Installation

### Via HACS (Recommandé)

1.  Ouvrez HACS dans Home Assistant.
2.  Cliquez sur les 3 points en haut à droite > **Dépôts personnalisés**.
3.  Ajoutez l'URL de ce dépôt : `https://github.com/ton-user/ha-groupe3f` (remplacez par votre URL réelle).
4.  Sélectionnez la catégorie **Intégration**.
5.  Cliquez sur **Installer**.
6.  Redémarrez Home Assistant.

### Manuelle

1.  Téléchargez la dernière release.
2.  Copiez le dossier `custom_components/groupe3f` dans votre dossier `config/custom_components`.
3.  Redémarrez Home Assistant.

## Configuration

1.  Allez dans **Paramètres** > **Appareils et services**.
2.  Cliquez sur **Ajouter une intégration** en bas à droite.
3.  Recherchez **Groupe 3F**.
4.  Entrez votre **Email** et votre **Mot de passe** (les mêmes que pour l'espace client web).
5.  Cliquez sur **Valider**.

### Authentification à deux facteurs (2FA)

Si c'est votre première connexion via Home Assistant, Groupe 3F demandera une vérification :

1.  Une nouvelle fenêtre apparaîtra vous demandant un **Code de vérification**.
2.  Consultez vos emails : vous devriez avoir reçu un code à 6 chiffres de la part de Groupe 3F.
3.  Entrez ce code dans Home Assistant et validez.

*Note : Cette étape n'est nécessaire qu'une seule fois. L'intégration simule un appareil de confiance pour ne plus avoir à redemander le code.*

## Dashboard Énergie

Pour suivre votre consommation d'eau dans le tableau de bord Énergie :

1.  Allez dans **Paramètres** > **Tableaux de bord** > **Énergie**.
2.  Cherchez la section **Consommation d'eau**.
3.  Cliquez sur **Ajouter une source d'eau**.
4.  Sélectionnez votre capteur (ex: `sensor.compteur_3f_eau_chaude`).
5.  Validez.

*L'historique de vos consommations passées apparaîtra progressivement dans le graphique.*