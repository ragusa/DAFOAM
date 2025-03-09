/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     |
    \\  /    A nd           | www.openfoam.com
     \\/     M anipulation  |
-------------------------------------------------------------------------------
    Copyright (C) 2019-2021 OpenCFD Ltd.
    Copyright (C) YEAR AUTHOR, AFFILIATION
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

\*---------------------------------------------------------------------------*/

#include "mixedFvPatchFieldTemplate.H"
#include "addToRunTimeSelectionTable.H"
#include "fvPatchFieldMapper.H"
#include "volFields.H"
#include "surfaceFields.H"
#include "unitConversion.H"
#include "PatchFunction1.H"

//{{{ begin codeInclude

//}}} end codeInclude


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

// * * * * * * * * * * * * * * * Local Functions * * * * * * * * * * * * * * //

//{{{ begin localCode

//}}} end localCode

// * * * * * * * * * * * * * * * Global Functions  * * * * * * * * * * * * * //

// dynamicCode:
// SHA1 = abd904e0242f0adb48be94f14273be958afdc09a
//
// unique function name that can be checked if the correct library version
// has been loaded
extern "C" void sinusoidal_at_left_bound_abd904e0242f0adb48be94f14273be958afdc09a(bool load)
{
    if (load)
    {
        // Code that can be explicitly executed after loading
    }
    else
    {
        // Code that can be explicitly executed before unloading
    }
}

// * * * * * * * * * * * * * * Static Data Members * * * * * * * * * * * * * //

makeRemovablePatchTypeField
(
    fvPatchScalarField,
    sinusoidal_at_left_boundMixedValueFvPatchScalarField
);

} // End namespace Foam


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::
sinusoidal_at_left_boundMixedValueFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF
)
:
    parent_bctype(p, iF)
{
    if (false)
    {
        printMessage("Construct sinusoidal_at_left_bound : patch/DimensionedField");
    }
}


Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::
sinusoidal_at_left_boundMixedValueFvPatchScalarField
(
    const sinusoidal_at_left_boundMixedValueFvPatchScalarField& rhs,
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const fvPatchFieldMapper& mapper
)
:
    parent_bctype(rhs, p, iF, mapper)
{
    if (false)
    {
        printMessage("Construct sinusoidal_at_left_bound : patch/DimensionedField/mapper");
    }
}


Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::
sinusoidal_at_left_boundMixedValueFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const dictionary& dict
)
:
    parent_bctype(p, iF, dict)
{
    if (false)
    {
        printMessage("Construct sinusoidal_at_left_bound : patch/dictionary");
    }
}


Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::
sinusoidal_at_left_boundMixedValueFvPatchScalarField
(
    const sinusoidal_at_left_boundMixedValueFvPatchScalarField& rhs
)
:
    parent_bctype(rhs),
    dictionaryContent(rhs)
{
    if (false)
    {
        printMessage("Copy construct sinusoidal_at_left_bound");
    }
}


Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::
sinusoidal_at_left_boundMixedValueFvPatchScalarField
(
    const sinusoidal_at_left_boundMixedValueFvPatchScalarField& rhs,
    const DimensionedField<scalar, volMesh>& iF
)
:
    parent_bctype(rhs, iF)
{
    if (false)
    {
        printMessage("Construct sinusoidal_at_left_bound : copy/DimensionedField");
    }
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::
~sinusoidal_at_left_boundMixedValueFvPatchScalarField()
{
    if (false)
    {
        printMessage("Destroy sinusoidal_at_left_bound");
    }
}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

void
Foam::
sinusoidal_at_left_boundMixedValueFvPatchScalarField::updateCoeffs()
{
    if (this->updated())
    {
        return;
    }

    if (false)
    {
        printMessage("updateCoeffs sinusoidal_at_left_bound");
    }

//{{{ begin code
    #line 26 "/home/grads/m/mahmudulhasantamim/openfoam/OpenFOAM-v2406/tutorials/basic/laplacianFoam/HeatPlateBoundaryTimeDependent/0/T/boundaryField/left"
const scalar amplitude = 1000;  // Amplitude of the sinusoidal gradient (in K/m)
            const scalar frequency = 1;  // Frequency in 1/m
	    const scalar freq_t = 0.01;
            const fvPatch& boundaryPatch = patch();
            scalarField& joe = this->refGrad();
            const scalar t=this->db().time().value();

            forAll(boundaryPatch, faceI)
            {
                // Use Cf() to get the face center coordinates and apply sinusoidal gradient
                joe[faceI] = amplitude * Foam::sin(Foam::constant::mathematical::pi * t * freq_t )* Foam::sin(Foam::constant::mathematical::pi * frequency * boundaryPatch.Cf()[faceI].y());
            }
//}}} end code

    this->parent_bctype::updateCoeffs();
}


// ************************************************************************* //

