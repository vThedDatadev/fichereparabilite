import streamlit as st
import sys
import os
import csv
import camelot
from pathlib import Path
import pandas as pd
import io
import tempfile

def extract_ind(file):
    try:
        tables = camelot.read_pdf(file)
        meta_data = None
        
        if isinstance(tables, camelot.core.TableList):
            table_count = len(tables)
            meta_table = tables[0].df
            
            # Transformation du DataFrame en texte condensé
            meta_text = ""
            for idx, row in meta_table.iterrows():
                # Joindre les cellules non vides de chaque ligne
                row_text = ' '.join([str(cell).strip() for cell in row if str(cell).strip() != ''])
                if row_text:  # Si la ligne n'est pas vide
                    meta_text += row_text + ' '
            
            # Supprimer les espaces multiples et nettoyer le texte
            meta_data = ' '.join(meta_text.split())
            print(f"test meta : {meta_data}")
            
        elif isinstance(tables, camelot.core.Table):    
            table_count = 1
            meta_table = tables[0].df
            meta_data = "Pas d'extraction possible"
            print(f"meta v2 {meta_data}")
        else:
            raise ValueError("Type de retour inattendu de camelot.read_pdf()")

        print(f"Nombre de tables : {table_count}")

        selected_table = None
        selected_table_index = 0
        for i in range(min(3, table_count)):
            current_table = tables[i].df
            if len(current_table) >= 5:
                selected_table = current_table
                selected_table_index = i
                print(f"Table sélectionnée : {i + 1}")
                break

        if selected_table is None:
            raise ValueError("Aucune table valide trouvée")

        col = len(selected_table.columns) - 1
        line = len(selected_table)
        print(f"Colonnes : {col + 1}, Lignes : {line}")

        result = selected_table.iloc[-1, col]
        
        return {
            'resultat': result,
            'meta': meta_data,
            'table_index': selected_table_index
        }

    except Exception as e:
        print(f"Une erreur s'est produite : {e}")
        return None

def process_pdf_files(files):
    results = []
    for uploaded_file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        result = extract_ind(tmp_file_path)
        if result is not None:
            print(f"not none : {result['meta']}")
            results.append([
                uploaded_file.name, 
                result['resultat'],
                result['meta'],
                result['table_index']
            ])

        os.unlink(tmp_file_path)  # Delete the temporary file

    return results

def main():
    st.title("Traitement des fichiers FREP")

    uploaded_files = st.file_uploader("Choisissez les fichiers FREP", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        st.write(f"{len(uploaded_files)} fichiers ont été chargés.")

        if st.button("Traiter les fichiers"):
            results = process_pdf_files(uploaded_files)

            if results:
                df = pd.DataFrame(results, columns=[
                    'Nom du fichier', 
                    'Résultat',
                    'meta',
                    'Index de la table'
                ])
                st.write("Résultats extraits:")
                st.dataframe(df)

                csv = df.to_csv(index=False).encode('utf-8')

                st.download_button(
                    label="Télécharger les résultats en CSV",
                    data=csv,
                    file_name="resultats_extraction.csv",
                    mime="text/csv",
                )
            else:
                st.error("Aucun résultat n'a pu être extrait des fichiers.")

if __name__ == "__main__":
    main()
