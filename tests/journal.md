# Problèmes de saisi de données découverts lors de la transformation vers le curblr.

Le document présente une liste des problèmes trouvé dans les données de l'inventaire. Dans la mesure du possible, il faut retrenscrir ces erreurs en tests.

## Résutlats

Les résultats des tests se trouvent dans le fichier `problemes_detecte_inventaire.log` présent dans le dossier test.

## Exception temporelles incohérante sur un même panneau

L'exemple du panneau `c1ca0bfa-5f4c-4e6d-afc7-f84fb77091f7` illustre une erreur de saisi de données dans la seconde ligne. Le champ RegTmpExcept est saisi à `oui` alors
que pour l'heure précédente il est saisi à `non`. Cette situation ne devrait pas arrivée et le champs de la deuxième ligne devrait être à `non` également (où alors il aurait fallu que l'information temporelle soit écrit à l'envers de sa représentation sur le panneau).

```python
df.loc[
    df.globalid_panneau == 'c1ca0bfa-5f4c-4e6d-afc7-f84fb77091f7',
    ['RegTmpExcept', 'RegTmpEcole', 'RegTmpHeureDebut',
    'RegTmpHeureFin', 'RegTmpJours', 'panneau_an_jour_debut',
     'panneau_an_jour_fin', 'RegVehType']
]
>>>    RegTmpExcept RegTmpEcole RegTmpHeureDebut RegTmpHeureFin                          RegTmpJours  panneau_an_jour_debut  panneau_an_jour_fin RegVehType
>>> 60          non        None         08:00:00       10:00:00  lundi,mardi,mercredi,jeudi,vendredi                    NaN                  NaN       None
>>> 60          oui        None         15:30:00       17:30:00  lundi,mardi,mercredi,jeudi,vendredi                    NaN                  NaN       None
```

## Exception de classe pour les zones SRRR

À Montréal, la grande majorité des panneau de stationnement qui réglemente l'usage de la bordure pour le stationnement des véhicules de résident (SRRR) sont définis comme : une interdiction de stationner et une exception pour les détenteurs de la vignette.
Dans l'exemple suivant, on remarque que les panneaux SRRR sont classées à la fois comme `parking` et `no parking`, mais ne présente jamais le champs `RegVehExcept` à `oui`. Un panneau SRRR désigné comme une interdiction de stationner sans exception pour les détenteurs de vignettes reproduira dans les données l'inverse de ce qui est attendu.


```python
df.loc[~df.RegVehSRRR.isna(), 'RegVehExcept'].unique()
>>> array([None, 'non'], dtype=object)
df.loc[~df.RegVehSRRR.isna(), 'RegNature'].unique()
>>> array(['permission', None, 'interdiction'], dtype=object)
```

## Des supports associés à une mauvaise rue

Dans les données, certains support sont, soit attachés à la mauvaise rue (ici le tronçon de la géobase), soit attachés à aucun tronçon de la géobase.

Les panneaux suivants ne sont pas rattachés à un segment de la géobase :
- `98f630de-4b2b-4520-8e67-62598834a146`
- `f030ed3e-9453-4b4b-aaa9-beaddbcbd08e`
- `7d61c57d-96bf-4d4b-a52d-038515f98574`
- `0f81e3b6-c68e-4a66-a065-7b87319d540d`
- `071f264d-861c-45b7-906c-4d533b58c259`
- `9931de6d-14d7-4131-8f10-802ce4a50035`
- `acd025d7-1f88-4a2e-9467-a41c2f507d33`
- `4ba44b31-fb07-4e33-996c-37e88f42ab72`
- `016e39ac-e59a-4478-9d66-ddb42e82c21e`

Les panneaux suivant sont ratachés au mauvais tronçon de la géobase. Ils ont été découvert car une réglementation de 0m est créé à cet endroit.
- `747f3e58-0233-47f3-80de-54dee165a631`
- `b006736b-a7d5-4579-a3f0-c67858d667a3`
- `a1e0d057-556d-49ca-9f06-6d13f40d78bd`

## Heures de début et de fin à 00:00:00

Si les heures de début et de fin sont indiquées à 00:00:00 la réglementation devient caduc.

## Une seule heure sur les deux de specifiée

Il n'est pas possible d'avoir une seule heure de spécifiée.

## Une seule des deux dates de specifiée

Il n'est pas possible d'avoir une seule des dates de spécifiée.

## Plusieurs début de zones pour une même réglementations

Si plusieurs panneaux sont sur la même rue et répète la même réglementation, ils ne devraient pas avoit plusieurs panneaux qui indiquent un commencement sans qu'un panneau indiquant une fin soit entre eux.

## Plusieurs fin de zones pour une même réglementations

Si plusieurs panneaux sont sur la même rue et répète la même réglementation, ils ne devraient pas avoit plusieurs panneaux qui indiquent une fin sans qu'un panneau indiquant un commencement soit entre eux.

# Éléments non testés

## TBD