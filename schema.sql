CREATE TABLE IF NOT EXISTS Beds (
    BedID INT PRIMARY KEY,
    BedLabel VARCHAR(255),
    BedDescription VARCHAR(255),
    Notizen VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Crops (
    CropID INT PRIMARY KEY,
    CropName VARCHAR(255),
    AlternativeNamen VARCHAR(255),
    CropSorte VARCHAR(255),
    CropFamilie VARCHAR(255),
    Notizen VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Plantings (
    PlantingID INT PRIMARY KEY,
    BedID INT,
    CropID INT,
    CropName VARCHAR(255),
    StartDate DATE,
    EndDate DATE,
    PlantingMethod VARCHAR(255),
    Notizen VARCHAR(255),
    FOREIGN KEY (BedID) REFERENCES Beds(BedID),
    FOREIGN KEY (CropID) REFERENCES Crops(CropID)
);

CREATE TABLE IF NOT EXISTS SoilImprovements (
    ImprovementID INT PRIMARY KEY,
    BedID INT,
    ImprovementName VARCHAR(255),
    StartDate DATE,
    EndDate DATE,
    Notizen VARCHAR(255),
    FOREIGN KEY (BedID) REFERENCES Beds(BedID)
);

CREATE TABLE IF NOT EXISTS AnbauInfos (
    AnbauID INT PRIMARY KEY,
    CropName VARCHAR(255),
    Intensität VARCHAR(255),
    NachbarnGut VARCHAR(255),
    NachbarnSchlecht VARCHAR(255),
    Keimdauer VARCHAR(255),
    Keimtemperatur VARCHAR(255),
    Saattiefe VARCHAR(255),
    Pflanztiefe VARCHAR(255),
    Pflanzenabstand VARCHAR(255),
    Reihenabstand VARCHAR(255),
    SäenVorziehenStart DATE,
    SäenVorziehenEnde DATE,
    SäenDirektStart1 DATE,
    SäenDirektEnde1 DATE,
    SäenDirektStart2 DATE,
    SäenDirektEnde2 DATE,
    SetzenStart1 DATE,
    SetzenEnde1 DATE,
    SetzenStart2 DATE,
    SetzenEnde2 DATE,
    SteckenStart1 DATE,
    SteckenEnde1 DATE,
    TagezurReifeGesäet INT,
    TagezurReifeGesetzt INT,
    TagezurReifeGesteckt INT,
    ErntefensterStart1 DATE,
    ErntefensterEnde1 DATE,
    ErntefensterStart2 DATE,
    ErntefensterEnde2 DATE,
    Notizen VARCHAR(255)
);