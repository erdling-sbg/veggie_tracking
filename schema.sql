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