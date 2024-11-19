import streamlit as st
import sys
import os
import csv
import camelot
from pathlib import Path
import pandas as pd
import io
import tempfile
from PyPDF2 import PdfReader

def extract_text_around_date_calcul(pdf_path):
    """Extrait 1 lignes avant et 2 lignes après avoir trouvé 'référence du modèle' dans le PDF entier"""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = page.extract_text()
            lines = text.split('\n')
            
            # Chercher la ligne contenant "date de calcul" (insensible à la casse)
            for i, line in enumerate(lines):
                if 'rence du' in line.lower():
                    # Calculer l'index de début (5 lignes avant, mais pas moins que 0)
                    start_idx = max(0, i - 1)
                    # Prendre les 5 lignes avant + la ligne courante + 30 lignes après
                    selected_lines = lines[start_idx:i+2]
                    return ' | '.join(selected_lines)
        
        return "Date de calcul non trouvée dans le PDF"
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte : {e}")
        return "Erreur lors de l'extraction du texte"

def find_date_calcul_index(df):
    """Trouve l'index de la ligne contenant 'date de calcul' (insensible à la casse)"""
    for idx, row in df.iterrows():
        row_text = ' '.join([str(cell).strip().lower() for cell in row if str(cell).strip() != '']).lower()
        if 'rence du' in row_text:
            return idx
    return None

def extract_ind(file):
    try:
        tables = camelot.read_pdf(file)
        meta_data = None
        
        if isinstance(tables, camelot.core.TableList):
            table_count = len(tables)
            
            # Si une seule table est trouvée
            if table_count == 1:
                # Chercher "Date de calcul" dans tout le PDF
                meta_data = extract_text_around_date_calcul(file)
                print(f"test meta (single table) : {meta_data}")
            else:
                # Comportement original pour plusieurs tables
                meta_table = tables[0].df
                meta_text = ""
                for idx, row in meta_table.iterrows():
                    row_text = ' '.join([str(cell).strip() for cell in row if str(cell).strip() != ''])
                    if row_text:
                        meta_text += row_text + ' '
                meta_data = ' '.join(meta_text.split())
                print(f"test meta (multiple tables) : {meta_data}")
            
        elif isinstance(tables, camelot.core.Table):    
            table_count = 1
            # Chercher "Date de calcul" dans tout le PDF
            meta_data = extract_text_around_date_calcul(file)
            print(f"meta v2 : {meta_data}")
        else:
            raise ValueError("Type de retour inattendu de camelot.read_pdf()")

        print(f"Nombre de tables : {table_count}")

        selected_table = None
        selected_table_index = 0
        for i in range(min(3, table_count)):
            current_table = tables[i].df if isinstance(tables, camelot.core.TableList) else tables.df
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
        # Remplacer la virgule par un point dans le résultat
        result = str(result).replace(',', '.')
        
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
    # Configuration de la page
    st.set_page_config(
        page_title="Analyse des fiches réparabilités",
        layout="wide"
    )

    # Création d'une disposition en colonnes pour le logo et le titre
    col1, col2 = st.columns([1, 4])
    
    # Ajout du logo dans la première colonne
    with col1:
        # Remplacez 'logo.png' par le chemin de votre logo
        st.image('logo.png', width=150)
    
    # Ajout du titre dans la deuxième colonne
    with col2:
        st.title("Analyse des fiches réparabilités")

    uploaded_files = st.file_uploader("Sélectionnez l'ensemble des fiches à traiter", type="pdf", accept_multiple_files=True)

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
