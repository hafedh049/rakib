# Marque de l'établissement

Déposer ici le fichier fourni par la banque :

    uib.svg

`Brandmark` (`src/components/Brandmark.tsx`) le charge automatiquement dès
qu'il est présent. Tant qu'il ne l'est pas, une composition typographique
prend le relais — carré rouge de marque et sigle — sans reproduire un
artwork que nous n'avons pas reçu.

L'artwork officiel est **une marque déposée et n'est délibérément pas
versionné** : le dépôt peut ainsi être partagé, évalué et archivé sans
rediffuser la marque d'un tiers.

Un SVG est préférable à un PNG (netteté à toute taille, quelques kilo-octets).
Si seul un PNG est disponible, le déposer sous `uib.png` et changer l'extension
dans `Brandmark.tsx`.
