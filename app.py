hw_files = st.sidebar.file_uploader(
    t["uploader_label_hw"],
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="hw_high_res_uploader"
)

if hw_files:
    with st.sidebar.status("🔄 Επεξεργασία & συμπίεση εκφώνησης...", expanded=True) as status:
        old_hw = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.startswith('hw_page_')]
        for p in old_hw:
            try:
                os.remove(p)
            except:
                pass

        total_hw = len(hw_files)
        for idx, hw_f in enumerate(hw_files):
            st.write(f"Συμπίεση αρχείου {idx + 1} από {total_hw}...")
            compressed_bytes = compress_image(hw_f.getbuffer())
            hw_path = os.path.join(UPLOAD_FOLDER, f"hw_page_{idx}.jpg")
            with open(hw_path, "wb") as f:
                f.write(compressed_bytes)
        status.update(label="✅ Η εκφώνηση αποθηκεύτηκε με επιτυχία!", state="complete", expanded=False)
